"""
PHASE 35: Credit Management Service
Handles all credit operations with immutable ledger tracking
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from models import CreditLedger, CreditActionType


class CreditService:
    """Service for managing credits with immutable ledger"""
    
    def __init__(self, db):
        self.db = db
        self.admins_collection = db['admins']
        self.ledger_collection = db['credit_ledger']
    
    async def add_credits(
        self,
        admin_id: str,
        amount: int,
        reason: str,
        performed_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add credits to an admin account
        Returns: Updated credit balance and ledger entry
        """
        # Get current admin data
        admin = await self.admins_collection.find_one({'id': admin_id})
        if not admin:
            raise ValueError(f"Admin with id {admin_id} not found")
        
        # Calculate new balance
        current_total = admin.get('total_credits', 0)
        new_total = current_total + amount
        
        # Update admin credits
        await self.admins_collection.update_one(
            {'id': admin_id},
            {'$set': {'total_credits': new_total}}
        )
        
        # Create ledger entry
        ledger_entry = CreditLedger(
            admin_id=admin_id,
            action_type=CreditActionType.ADD,
            amount=amount,
            balance_before=current_total,
            balance_after=new_total,
            reason=reason,
            performed_by=performed_by,
            metadata=metadata
        )
        
        await self.ledger_collection.insert_one(ledger_entry.model_dump())
        
        return {
            'success': True,
            'admin_id': admin_id,
            'total_credits': new_total,
            'used_credits': admin.get('used_credits', 0),
            'available_credits': new_total - admin.get('used_credits', 0),
            'ledger_id': ledger_entry.credit_id
        }
    
    async def deduct_credits(
        self,
        admin_id: str,
        amount: int,
        reason: str,
        performed_by: str,
        related_wedding_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deduct credits from an admin account (manual deduction)
        Returns: Updated credit balance and ledger entry
        """
        # Get current admin data
        admin = await self.admins_collection.find_one({'id': admin_id})
        if not admin:
            raise ValueError(f"Admin with id {admin_id} not found")
        
        # Calculate new balance
        current_total = admin.get('total_credits', 0)
        new_total = current_total - amount
        
        # Prevent negative balance
        if new_total < 0:
            raise ValueError(f"Insufficient credits. Current: {current_total}, Attempting to deduct: {amount}")
        
        # Update admin credits
        await self.admins_collection.update_one(
            {'id': admin_id},
            {'$set': {'total_credits': new_total}}
        )
        
        # Create ledger entry
        ledger_entry = CreditLedger(
            admin_id=admin_id,
            action_type=CreditActionType.DEDUCT,
            amount=-amount,  # Negative for deduction
            balance_before=current_total,
            balance_after=new_total,
            reason=reason,
            related_wedding_id=related_wedding_id,
            performed_by=performed_by,
            metadata=metadata
        )
        
        await self.ledger_collection.insert_one(ledger_entry.model_dump())
        
        return {
            'success': True,
            'admin_id': admin_id,
            'total_credits': new_total,
            'used_credits': admin.get('used_credits', 0),
            'available_credits': new_total - admin.get('used_credits', 0),
            'ledger_id': ledger_entry.credit_id
        }
    
    async def use_credits(
        self,
        admin_id: str,
        amount: int,
        reason: str,
        related_wedding_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use credits (called on publish action)
        This increments used_credits, not deducting from total_credits
        Returns: Updated credit balance and ledger entry
        """
        # Get current admin data
        admin = await self.admins_collection.find_one({'id': admin_id})
        if not admin:
            raise ValueError(f"Admin with id {admin_id} not found")
        
        # Check available credits
        current_total = admin.get('total_credits', 0)
        current_used = admin.get('used_credits', 0)
        available = current_total - current_used
        
        if available < amount:
            raise ValueError(f"Insufficient credits. Available: {available}, Required: {amount}")
        
        # Update used credits
        new_used = current_used + amount
        
        await self.admins_collection.update_one(
            {'id': admin_id},
            {'$set': {'used_credits': new_used}}
        )
        
        # Create ledger entry
        ledger_entry = CreditLedger(
            admin_id=admin_id,
            action_type=CreditActionType.USED,
            amount=-amount,  # Negative for usage
            balance_before=available,
            balance_after=available - amount,
            reason=reason,
            related_wedding_id=related_wedding_id,
            performed_by=admin_id,  # Admin themselves
            metadata=metadata
        )
        
        await self.ledger_collection.insert_one(ledger_entry.model_dump())
        
        return {
            'success': True,
            'admin_id': admin_id,
            'total_credits': current_total,
            'used_credits': new_used,
            'available_credits': current_total - new_used,
            'ledger_id': ledger_entry.credit_id
        }
    
    async def get_credit_balance(self, admin_id: str) -> Dict[str, int]:
        """Get current credit balance for an admin"""
        admin = await self.admins_collection.find_one({'id': admin_id})
        if not admin:
            raise ValueError(f"Admin with id {admin_id} not found")
        
        total = admin.get('total_credits', 0)
        used = admin.get('used_credits', 0)
        
        return {
            'total_credits': total,
            'used_credits': used,
            'available_credits': total - used
        }
    
    async def get_credit_ledger(
        self,
        admin_id: str,
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Get credit transaction history for an admin"""
        # Get ledger entries
        cursor = self.ledger_collection.find({'admin_id': admin_id})
        cursor = cursor.sort('created_at', -1).skip(skip).limit(limit)
        
        entries = []
        async for entry in cursor:
            entry['_id'] = str(entry['_id'])
            entries.append(entry)
        
        # Get total count
        total = await self.ledger_collection.count_documents({'admin_id': admin_id})
        
        return {
            'entries': entries,
            'total': total,
            'limit': limit,
            'skip': skip
        }
    
    async def adjust_credits(
        self,
        admin_id: str,
        amount: int,
        reason: str,
        performed_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manual credit adjustment (can be positive or negative)
        Used for corrections or special cases
        """
        # Get current admin data
        admin = await self.admins_collection.find_one({'id': admin_id})
        if not admin:
            raise ValueError(f"Admin with id {admin_id} not found")
        
        # Calculate new balance
        current_total = admin.get('total_credits', 0)
        new_total = current_total + amount  # amount can be negative
        
        # Prevent negative balance
        if new_total < 0:
            raise ValueError(f"Adjustment would result in negative balance. Current: {current_total}, Adjustment: {amount}")
        
        # Update admin credits
        await self.admins_collection.update_one(
            {'id': admin_id},
            {'$set': {'total_credits': new_total}}
        )
        
        # Create ledger entry
        ledger_entry = CreditLedger(
            admin_id=admin_id,
            action_type=CreditActionType.ADJUST,
            amount=amount,
            balance_before=current_total,
            balance_after=new_total,
            reason=reason,
            performed_by=performed_by,
            metadata=metadata
        )
        
        await self.ledger_collection.insert_one(ledger_entry.model_dump())
        
        return {
            'success': True,
            'admin_id': admin_id,
            'total_credits': new_total,
            'used_credits': admin.get('used_credits', 0),
            'available_credits': new_total - admin.get('used_credits', 0),
            'ledger_id': ledger_entry.credit_id
        }

    async def refund_credits(
        self,
        admin_id: str,
        amount: int,
        reason: str,
        performed_by: str,
        related_wedding_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Refund previously-used credits back to the account (e.g. unpublish).
        Decrements `used_credits` (never below zero) and writes a REFUND ledger row.
        """
        if amount <= 0:
            raise ValueError("Refund amount must be a positive integer")
        admin = await self.admins_collection.find_one({'id': admin_id})
        if not admin:
            raise ValueError(f"Admin with id {admin_id} not found")

        current_total = admin.get('total_credits', 0)
        current_used  = admin.get('used_credits', 0)
        # Clamp so we never go below zero used_credits.
        refund_amount = min(amount, current_used)
        new_used = current_used - refund_amount
        available_before = current_total - current_used
        available_after  = current_total - new_used

        await self.admins_collection.update_one(
            {'id': admin_id},
            {'$set': {'used_credits': new_used}}
        )

        ledger_entry = CreditLedger(
            admin_id=admin_id,
            action_type=CreditActionType.REFUND,
            amount=refund_amount,                  # +ve per spec
            balance_before=available_before,
            balance_after=available_after,
            reason=reason,
            related_wedding_id=related_wedding_id,
            performed_by=performed_by,
            metadata=metadata,
        )
        await self.ledger_collection.insert_one(ledger_entry.model_dump())

        return {
            'success': True,
            'admin_id': admin_id,
            'total_credits': current_total,
            'used_credits': new_used,
            'available_credits': available_after,
            'refunded': refund_amount,
            'ledger_id': ledger_entry.credit_id,
        }
