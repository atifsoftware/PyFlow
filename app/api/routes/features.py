"""
app/api/routes/features.py
===========================
FastAPI-তে নতুন v3.0.0 ফিচারগুলোর (PostgreSQL, Precision Math, Atomic Transactions)
ইন্টারেক্টিভ টেস্ট এন্ডপয়েন্ট। সোয়াগার ডক্স (/api/docs) থেকে সরাসরি টেস্ট করা যাবে।
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from core.decimal_math import Money, number_to_words, MoneyError
from core.database import Database, QueryError, atomic

router = APIRouter()


# ─── Schema Definitions ──────────────────────────────────────────────────────

class MoneyRequest(BaseModel):
    amount: str = Field(..., example="120500.50", description="পরিমাণ (যেমন: 120500.50)")
    currency: str = Field(default="BDT", example="BDT", description="মুদ্রা (BDT, USD, EUR, INR)")
    lang: str = Field(default="bn", example="bn", description="ভাষা: 'bn' বা 'en'")
    style: Optional[str] = Field(default="indian", example="indian", description="স্টাইল: 'indian' বা 'international' (শুধু ইংরেজি ভাষার জন্য)")


class TransactionRequest(BaseModel):
    name: str = Field(..., example="TxUser", description="ব্যবহারকারীর নাম")
    email: str = Field(..., example="txuser@example.com", description="ইমেল")
    should_fail: bool = Field(default=False, description="True দিলে ট্রানজেকশনে ইচ্ছাকৃত error তৈরি করবে (রোলব্যাক টেস্ট)")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/money-convert", summary="আর্থিক পরিমাণ কথায় রূপান্তর (Number to Words)")
async def money_convert(payload: MoneyRequest):
    """
    Precision Money Math এবং Number to Words রূপান্তরকারী টেস্ট এন্ডপয়েন্ট।
    
    - BDT / USD / EUR / INR মুদ্রা সমর্থন করে।
    - বাংলা ও ইংরেজিতে কথায় অনুবাদ করে।
    - ইংরেজিতে ভারতীয়/দেশী (Lakh/Crore) এবং আন্তর্জাতিক (Million/Billion) স্টাইল সমর্থন করে।
    """
    try:
        m = Money(payload.amount, payload.currency)
        words = m.to_words(lang=payload.lang, style=payload.style)
        return {
            "amount": float(m.amount),
            "currency": m.currency,
            "formatted": m.format(symbol=True),
            "words": words,
            "paisa": m.to_paisa(),
        }
    except MoneyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/transaction-test", summary="অ্যাটমিক ট্রানজেকশন সফল/ব্যর্থ টেস্ট")
async def transaction_test(payload: TransactionRequest):
    """
    অ্যাটমিক ট্রানজেকশন রোলব্যাক ও কমিট টেস্ট এন্ডপয়েন্ট।
    
    - **should_fail = False** দিলে ট্রানজেকশন সফল হবে এবং ইউজার ডাটাবেজে সেভ হবে।
    - **should_fail = True** দিলে ট্রানজেকশন চলাকালীন ValueError তৈরি করে রোলব্যাক করবে (ডাটাবেজে কোনো ইউজার যুক্ত হবে না)।
    """
    import time
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        # nested/atomic block test
        with Database.transaction():
            # Insert operation 1
            from core.query_builder import QueryBuilder
            uid = QueryBuilder("users").insert({
                "name": payload.name,
                "email": payload.email,
                "password": "x",
                "role": "user",
                "created_at": now,
                "updated_at": now,
            })
            
            # error logic if should_fail is enabled
            if payload.should_fail:
                raise ValueError("ইচ্ছাকৃত এরর — ডাটা রোলব্যাক করা হয়েছে!")
                
            # commit-এর পর চালানোর জন্য হুক রেজিস্টার
            called_hooks = []
            Database.on_commit(lambda: called_hooks.append("Email sent successfully!"))

        return {
            "status": "success",
            "message": "ট্রানজেকশন সফল ও ডাটা কমিট হয়েছে!",
            "user_id": uid,
            "on_commit_hooks": called_hooks
        }
        
    except Exception as exc:
        # logic verify: insert করা user টি ডাটাবেজে মুছে গেছে কিনা চেক করি
        from core.query_builder import QueryBuilder
        exists = QueryBuilder("users").where("email", payload.email).exists()
        
        return {
            "status": "rolled_back",
            "message": f"ট্রানজেকশন রোলব্যাক হয়েছে। কারণ: {str(exc)}",
            "exists_in_database": exists
        }


@router.get("/db-status", summary="ডাটাবেজ সংযোগ পুল স্ট্যাটাস")
async def db_status():
    """
    Database Pool-এর সংযোগ ড্রাইভার ও থ্রেড-সেফ অ্যাক্টিভ কানেকশনের লাইভ স্ট্যাটাস।
    """
    try:
        status = Database.get_status()
        return {
            "status": "online",
            "database": status
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
