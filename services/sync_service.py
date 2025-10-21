"""Main sync service for coordinating synchronization"""
import asyncio
from typing import Dict, List, Set
from db.database_manager import DatabaseManager
from services.letterboxd_service import LetterboxdService
from models.sync_models import SyncGroup, GroupMember, SyncMode, OperationType, SyncResult
import logging

logger = logging.getLogger(__name__)


class SyncService:
    """Main service for managing sync operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.letterboxd_service = LetterboxdService()
        self.list_id_cache = {}  # Cache list IDs

    async def get_list_id_for_member(self, member: GroupMember) -> str:
        """Get list ID for a member, with caching"""
        # Check cache first
        if member.id in self.list_id_cache:
            return self.list_id_cache[member.id]

        # Check database cache
        if member.list_id:
            self.list_id_cache[member.id] = member.list_id
            return member.list_id

        # Extract from Letterboxd
        list_id = await self.letterboxd_service.get_list_id_for_member(member)
        if list_id:
            self.list_id_cache[member.id] = list_id
            self.db.update_member_list_id(member.id, list_id)
            member.list_id = list_id  # Update the object

        return list_id

    async def sync_master_slave_group(self, group: SyncGroup) -> SyncResult:
        """Sync a master-slave group"""
        members = self.db.get_group_members(group.id)
        if not members:
            return SyncResult(success=False, group_id=group.id, errors=["No members found"])

        # Find master
        master = next((m for m in members if m.is_master), None)
        if not master:
            return SyncResult(success=False, group_id=group.id, errors=["No master found"])

        slaves = [m for m in members if not m.is_master]
        logger.info(f"Syncing master-slave group {group.id}: 1 master, {len(slaves)} slaves")

        # Get current state of master's list
        master_movies = await self.letterboxd_service.get_movies_from_list(master)
        if not master_movies:
            return SyncResult(success=False, group_id=group.id,
                              errors=[f"Could not fetch movies from master {master.display_name}"])

        # Update master's state in DB
        for film_id in master_movies:
            self.db.update_user_movie_state(master.id, film_id, True)

        result = SyncResult(success=True, group_id=group.id)

        # Sync each slave to match master
        for slave in slaves:
            try:
                # Get list ID for this slave
                list_id = await self.get_list_id_for_member(slave)
                if not list_id:
                    result.errors.append(f"Could not get list ID for {slave.display_name}")
                    continue

                # Get slave's current list
                slave_movies = await self.letterboxd_service.get_movies_from_list(slave)

                # Calculate differences
                movies_to_add = master_movies - slave_movies
                movies_to_remove = slave_movies - master_movies

                logger.info(f"Slave {slave.display_name}: +{len(movies_to_add)}, -{len(movies_to_remove)}")

                # Add missing movies
                for film_id in movies_to_add:
                    success = await self.letterboxd_service.add_movie_to_list(slave, film_id, list_id)
                    if success:
                        self.db.update_user_movie_state(slave.id, film_id, True)
                        self.db.log_sync_operation(
                            group.id, OperationType.ADD_MOVIE, film_id,
                            master.id, slave.id, True
                        )
                        result.operations.append(f"Added {film_id} to {slave.display_name}")
                        result.operations_count += 1
                    else:
                        self.db.log_sync_operation(
                            group.id, OperationType.ADD_MOVIE, film_id,
                            master.id, slave.id, False, "Add operation failed"
                        )
                        result.errors.append(f"Failed to add {film_id} to {slave.display_name}")
                        result.errors_count += 1

                # Remove extra movies
                for film_id in movies_to_remove:
                    success = await self.letterboxd_service.remove_movie_from_list(slave, film_id)
                    if success:
                        self.db.update_user_movie_state(slave.id, film_id, False)
                        self.db.log_sync_operation(
                            group.id, OperationType.REMOVE_MOVIE, film_id,
                            master.id, slave.id, True
                        )
                        result.operations.append(f"Removed {film_id} from {slave.display_name}")
                        result.operations_count += 1
                    else:
                        self.db.log_sync_operation(
                            group.id, OperationType.REMOVE_MOVIE, film_id,
                            master.id, slave.id, False, "Remove operation failed"
                        )
                        result.errors.append(f"Failed to remove {film_id} from {slave.display_name}")
                        result.errors_count += 1

            except Exception as e:
                logger.error(f"Error syncing slave {slave.display_name}: {e}")
                result.errors.append(f"Error syncing {slave.display_name}: {str(e)}")
                result.errors_count += 1

        self.db.update_last_sync(group.id)
        return result

    async def sync_collaborative_group(self, group: SyncGroup) -> SyncResult:
        """Sync a collaborative group"""
        members = self.db.get_group_members(group.id)
        if not members:
            return SyncResult(success=False, group_id=group.id, errors=["No members found"])

        logger.info(f"Syncing collaborative group {group.id}: {len(members)} members")

        # Get current state of all members' lists
        member_movies = {}
        all_movies = set()

        for member in members:
            current_movies = await self.letterboxd_service.get_movies_from_list(member)
            member_movies[member.id] = current_movies
            all_movies.update(current_movies)

            # Update member's state in DB
            for film_id in current_movies:
                self.db.update_user_movie_state(member.id, film_id, True)

        logger.info(f"Total unique movies across all members: {len(all_movies)}")

        result = SyncResult(success=True, group_id=group.id)

        # Sync each member to have all movies
        for member in members:
            try:
                # Get list ID
                list_id = await self.get_list_id_for_member(member)
                if not list_id:
                    result.errors.append(f"Could not get list ID for {member.display_name}")
                    continue

                current_member_movies = member_movies[member.id]
                missing_movies = all_movies - current_member_movies

                logger.info(f"{member.display_name} needs {len(missing_movies)} movies")

                # Add missing movies
                for film_id in missing_movies:
                    success = await self.letterboxd_service.add_movie_to_list(member, film_id, list_id)
                    if success:
                        self.db.update_user_movie_state(member.id, film_id, True)

                        # Find who originally had this movie
                        source_member = None
                        for other_member in members:
                            if other_member.id != member.id and film_id in member_movies[other_member.id]:
                                source_member = other_member
                                break

                        self.db.log_sync_operation(
                            group.id, OperationType.ADD_MOVIE, film_id,
                            source_member.id if source_member else None,
                            member.id, True
                        )
                        result.operations.append(f"Added {film_id} to {member.display_name}")
                        result.operations_count += 1
                    else:
                        self.db.log_sync_operation(
                            group.id, OperationType.ADD_MOVIE, film_id,
                            None, member.id, False, "Add operation failed"
                        )
                        result.errors.append(f"Failed to add {film_id} to {member.display_name}")
                        result.errors_count += 1

            except Exception as e:
                logger.error(f"Error syncing member {member.display_name}: {e}")
                result.errors.append(f"Error syncing {member.display_name}: {str(e)}")
                result.errors_count += 1

        self.db.update_last_sync(group.id)
        return result

    async def sync_group(self, group_id: int) -> SyncResult:
        """Sync a single group"""
        # Get all active groups and find the one we want
        groups = self.db.get_all_active_sync_groups()
        group = next((g for g in groups if g.id == group_id), None)

        if not group:
            return SyncResult(success=False, group_id=group_id,
                              errors=[f"Group {group_id} not found"])

        logger.info(f"Starting sync for group {group.id} ({group.group_name}) in {group.sync_mode.value} mode")

        try:
            if group.sync_mode == SyncMode.MASTER_SLAVE:
                return await self.sync_master_slave_group(group)
            elif group.sync_mode == SyncMode.COLLABORATIVE:
                return await self.sync_collaborative_group(group)
            else:
                return SyncResult(success=False, group_id=group.id,
                                  errors=[f"Unknown sync mode: {group.sync_mode}"])

        except Exception as e:
            logger.error(f"Error syncing group {group.id}: {e}")
            return SyncResult(success=False, group_id=group.id, errors=[str(e)])

    async def sync_all_groups(self) -> Dict:
        """Sync all active groups"""
        groups = self.db.get_all_active_sync_groups()

        if not groups:
            return {'success': True, 'message': 'No groups to sync', 'results': []}

        logger.info(f"Starting sync for {len(groups)} groups")

        results = []
        for group in groups:
            result = await self.sync_group(group.id)
            results.append({
                'group_id': group.id,
                'group_name': group.group_name,
                'success': result.success,
                'operations_count': result.operations_count,
                'errors_count': result.errors_count,
                'operations': result.operations,
                'errors': result.errors
            })

        return {
            'success': True,
            'groups_processed': len(groups),
            'results': results
        }