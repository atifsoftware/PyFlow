"""
core/decimal_math.py
=====================
আর্থিক হিসাবের জন্য নির্ভুল Decimal গণনা।

কেন float ব্যবহার করা যাবে না:
    >>> 0.1 + 0.2
    0.30000000000000004          # ভুল!
    >>> 0.1 + 0.2 == 0.3
    False                        # বিপদজনক!

    # ১ কোটি লেনদেনে এই পার্থক্য = কোটি টাকার গরমিল!

Money class এই সমস্যার সমাধান:
    >>> Money(100.50) + Money(200.25)
    Money('300.75 BDT')
    >>> Money(100.50) + Money(200.25) == Money(300.75)
    True                         # সঠিক!

ব্যবহার:
    from core.decimal_math import Money, money, percent_of, split_amount

    price   = Money(1500.00)
    tax     = percent_of(price, 15)       # ১৫% ভ্যাট
    total   = price + tax                 # Money('1725.00 BDT')
    parts   = split_amount(total, 3)      # [575.00, 575.00, 575.00]

    # Database থেকে পড়া (পয়সায় সংরক্ষিত)
    amount  = Money.from_paisa(172500)    # 1725.00 BDT
    stored  = amount.to_paisa()           # 172500

    # Formatting
    print(amount.format())                # ১,৭২৫.০০
    print(amount.format(symbol=True))     # ৳ ১,৭২৫.০০
"""

from __future__ import annotations

import math
from decimal import (
    Decimal,
    ROUND_HALF_UP,
    ROUND_FLOOR,
    ROUND_CEILING,
    InvalidOperation,
)
from typing import Union

# ─────────────────────────────── Type Alias ───────────────────────────────────

Numeric = Union[int, float, str, Decimal, "Money"]


# ─────────────────────────────── Exceptions ───────────────────────────────────

class MoneyError(Exception):
    """Money গণনায় ত্রুটি"""
    pass


class CurrencyMismatchError(MoneyError):
    """দুটো ভিন্ন currency-র Money যোগ/বিয়োগ করার চেষ্টা"""
    pass


# ─────────────────────────────── Money Class ─────────────────────────────────

class Money:
    """
    আর্থিক পরিমাণ নির্ভুলভাবে সংরক্ষণ ও গণনার জন্য।

    বৈশিষ্ট্য:
        - ২ দশমিক পর্যন্ত নির্ভুল (পয়সা পর্যন্ত)
        - ROUND_HALF_UP পদ্ধতি (বাংলাদেশের হিসাব নিয়ম)
        - Currency মিলছে কিনা সর্বদা যাচাই করে
        - Immutable — একবার তৈরি হলে পরিবর্তন হয় না
        - Database-এ পয়সা (integer) হিসেবে সংরক্ষণ

    উদাহরণ:
        price    = Money(1500)
        discount = Money("150.50")
        net      = price - discount          # Money('1349.50 BDT')
        vat      = net * Decimal("0.15")     # Money('202.43 BDT')
        total    = net + vat                 # Money('1551.93 BDT')
    """

    # ডিফোল্ট currency — পরিবর্তন করা যাবে
    DEFAULT_CURRENCY: str = "BDT"

    # দশমিক স্থান — সাধারণত ২ (পয়সা পর্যন্ত)
    DECIMAL_PLACES: int = 2

    __slots__ = ("_amount", "_currency")

    def __init__(
        self,
        amount: Numeric = 0,
        currency: str | None = None,
    ):
        """
        Money তৈরি করা।

        Args:
            amount:   পরিমাণ (int, float, str, Decimal, বা আরেকটা Money)
            currency: মুদ্রার কোড, default 'BDT'

        উদাহরণ:
            Money(100)           # 100.00 BDT
            Money("1500.50")     # 1500.50 BDT
            Money(99.9)          # 99.90 BDT
            Money(500, "USD")    # 500.00 USD
        """
        self._currency = (currency or self.DEFAULT_CURRENCY).upper().strip()

        if isinstance(amount, Money):
            if amount._currency != self._currency:
                raise CurrencyMismatchError(
                    f"Currency মিলছে না: {amount._currency} ≠ {self._currency}"
                )
            self._amount = amount._amount
            return

        try:
            raw = Decimal(str(amount))
            quant = Decimal(10) ** -self.DECIMAL_PLACES  # "0.01"
            self._amount = raw.quantize(quant, rounding=ROUND_HALF_UP)
        except InvalidOperation as exc:
            raise MoneyError(
                f"অবৈধ পরিমাণ: {amount!r} — শুধু সংখ্যা গ্রহণযোগ্য"
            ) from exc

    # ─────────────────── Properties ────────────────────────────────────────────

    @property
    def amount(self) -> Decimal:
        """Decimal পরিমাণ"""
        return self._amount

    @property
    def currency(self) -> str:
        """Currency কোড (যেমন 'BDT', 'USD')"""
        return self._currency

    @property
    def is_zero(self) -> bool:
        """পরিমাণ শূন্য কিনা"""
        return self._amount == Decimal("0.00")

    @property
    def is_positive(self) -> bool:
        """পরিমাণ ধনাত্মক কিনা"""
        return self._amount > Decimal("0.00")

    @property
    def is_negative(self) -> bool:
        """পরিমাণ ঋণাত্মক কিনা"""
        return self._amount < Decimal("0.00")

    # ─────────────────── Arithmetic ────────────────────────────────────────────

    def _ensure_same_currency(self, other: "Money") -> None:
        if self._currency != other._currency:
            raise CurrencyMismatchError(
                f"ভিন্ন currency যোগ/বিয়োগ করা যাবে না: "
                f"{self._currency} ≠ {other._currency}"
            )

    def __add__(self, other: Numeric) -> "Money":
        """Money + Money  বা  Money + number"""
        if isinstance(other, Money):
            self._ensure_same_currency(other)
            return Money(self._amount + other._amount, self._currency)
        return Money(self._amount + Decimal(str(other)), self._currency)

    def __radd__(self, other: Numeric) -> "Money":
        """number + Money  (sum() এর জন্য দরকার)"""
        if other == 0:
            return self  # sum([money1, money2, ...]) শুরু হয় 0 থেকে
        return self.__add__(other)

    def __sub__(self, other: Numeric) -> "Money":
        """Money - Money  বা  Money - number"""
        if isinstance(other, Money):
            self._ensure_same_currency(other)
            return Money(self._amount - other._amount, self._currency)
        return Money(self._amount - Decimal(str(other)), self._currency)

    def __rsub__(self, other: Numeric) -> "Money":
        """number - Money"""
        return Money(Decimal(str(other)) - self._amount, self._currency)

    def __mul__(self, factor: Union[int, float, str, Decimal]) -> "Money":
        """Money × সংখ্যা (হার বা পরিমাণ)"""
        if isinstance(factor, Money):
            raise MoneyError("Money × Money গণনা হয় না — Money × Decimal ব্যবহার করুন")
        return Money(self._amount * Decimal(str(factor)), self._currency)

    def __rmul__(self, factor) -> "Money":
        """সংখ্যা × Money"""
        return self.__mul__(factor)

    def __truediv__(self, divisor: Union[int, float, str, Decimal]) -> "Money":
        """Money ÷ সংখ্যা"""
        if isinstance(divisor, Money):
            raise MoneyError("Money ÷ Money সরাসরি করা যায় না — .amount ব্যবহার করুন")
        d = Decimal(str(divisor))
        if d == Decimal("0"):
            raise MoneyError("শূন্য দিয়ে ভাগ করা যাবে না")
        return Money(self._amount / d, self._currency)

    def __neg__(self) -> "Money":
        """-Money"""
        return Money(-self._amount, self._currency)

    def __abs__(self) -> "Money":
        """|Money|"""
        return Money(abs(self._amount), self._currency)

    # ─────────────────── Comparison ────────────────────────────────────────────

    def __eq__(self, other) -> bool:
        if isinstance(other, Money):
            return self._currency == other._currency and self._amount == other._amount
        try:
            return self._amount == Decimal(str(other))
        except (InvalidOperation, TypeError):
            return NotImplemented

    def __lt__(self, other: "Money") -> bool:
        if isinstance(other, Money):
            self._ensure_same_currency(other)
            return self._amount < other._amount
        return self._amount < Decimal(str(other))

    def __le__(self, other: "Money") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Money") -> bool:
        if isinstance(other, Money):
            self._ensure_same_currency(other)
            return self._amount > other._amount
        return self._amount > Decimal(str(other))

    def __ge__(self, other: "Money") -> bool:
        return self == other or self > other

    def __bool__(self) -> bool:
        """if money:  → শূন্য হলে False"""
        return not self.is_zero

    def __hash__(self):
        return hash((self._amount, self._currency))

    # ─────────────────── Rounding ──────────────────────────────────────────────

    def round(self, places: int = 2, rounding=ROUND_HALF_UP) -> "Money":
        """
        নির্দিষ্ট দশমিক স্থানে গোল করা।

        ব্যবহার:
            Money("1234.567").round(2)  →  Money("1234.57")
            Money("1234.567").round(0)  →  Money("1235.00")
        """
        quant = Decimal(10) ** -places
        return Money(
            self._amount.quantize(quant, rounding=rounding),
            self._currency,
        )

    def floor(self) -> "Money":
        """নিচে গোল করা (ট্যাক্স গণনায় কখনো কখনো দরকার)"""
        return self.round(0, rounding=ROUND_FLOOR)

    def ceiling(self) -> "Money":
        """উপরে গোল করা"""
        return self.round(0, rounding=ROUND_CEILING)

    # ─────────────────── Database I/O ─────────────────────────────────────────

    def to_paisa(self) -> int:
        """
        Database-এ integer (পয়সা) হিসেবে সংরক্ষণের জন্য।
        ১ টাকা = ১০০ পয়সা।

        সুবিধা:
            - Integer দিয়ে floating point সমস্যা নেই
            - Database-এ স্থান কম লাগে
            - Indexing দ্রুত হয়

        উদাহরণ:
            Money(1725.50).to_paisa()  →  172550
        """
        return int(self._amount * Decimal("100"))

    @classmethod
    def from_paisa(cls, paisa: int, currency: str | None = None) -> "Money":
        """
        Database থেকে পড়া পয়সার পরিমাণকে Money-তে রূপান্তর।

        উদাহরণ:
            Money.from_paisa(172550)  →  Money("1725.50 BDT")
        """
        return cls(Decimal(str(paisa)) / Decimal("100"), currency)

    def to_decimal(self) -> Decimal:
        """Decimal হিসেবে পাওয়া (SQL query-তে দেওয়ার জন্য)"""
        return self._amount

    def to_float(self) -> float:
        """
        float হিসেবে পাওয়া।
        সতর্কতা: শুধু display-এর জন্য, হিসাবে ব্যবহার করবেন না।
        """
        return float(self._amount)

    def to_str(self) -> str:
        """String হিসেবে পাওয়া (যেমন '1725.50')"""
        return str(self._amount)

    # ─────────────────── Formatting ───────────────────────────────────────────

    def format(
        self,
        symbol: bool = False,
        separator: str = ",",
        decimal_sep: str = ".",
        bangla_digits: bool = False,
    ) -> str:
        """
        মানুষের পড়ার উপযোগী ফরম্যাটে রূপান্তর।

        Args:
            symbol:        True হলে মুদ্রা চিহ্ন (৳) যোগ করবে
            separator:     হাজার বিভাজক (default: ',')
            decimal_sep:   দশমিক বিভাজক (default: '.')
            bangla_digits: True হলে বাংলা সংখ্যায় (০১২৩...)

        উদাহরণ:
            Money(1725500).format()                     →  '1,725,500.00'
            Money(1725500).format(symbol=True)          →  '৳ 1,725,500.00'
            Money(1725500).format(bangla_digits=True)   →  '১,৭২৫,৫০০.০০'
        """
        # Integer ও decimal অংশ আলাদা করা
        parts = f"{self._amount:.{self.DECIMAL_PLACES}f}".split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"

        # Negative handle করা
        negative = integer_part.startswith("-")
        if negative:
            integer_part = integer_part[1:]

        # ভারতীয় উপমহাদেশীয় format (প্রথম ৩, তারপর ২ করে)
        # যেমন: 1,72,55,00,000
        # তবে সহজ international format ব্যবহার করছি: 1,725,500
        formatted_int = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = separator + formatted_int
            formatted_int = digit + formatted_int

        result = f"{formatted_int}{decimal_sep}{decimal_part}"
        if negative:
            result = f"-{result}"

        # বাংলা সংখ্যায় রূপান্তর (প্রয়োজনে)
        if bangla_digits:
            bangla_map = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
            result = result.translate(bangla_map)

        # মুদ্রা চিহ্ন যোগ করা
        if symbol:
            currency_symbols = {
                "BDT": "৳",
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "INR": "₹",
            }
            sym = currency_symbols.get(self._currency, self._currency)
            result = f"{sym} {result}"

        return result

    def to_words(self, lang: str = "bn", style: str | None = None) -> str:
        """
        Money পরিমাণকে কথায় রূপান্তর করে (বাংলা ও ইংরেজি)।

        Args:
            lang:  'bn' (বাংলা) অথবা 'en' (ইংরেজি)
            style: 'indian' (Lakh/Crore) বা 'international' (Million/Billion)
                   (শুধু ইংরেজিতে প্রযোজ্য, default BDT/INR-এর জন্য 'indian')

        উদাহরণ:
            Money("120500.50").to_words('bn')  → "এক লক্ষ বিশ হাজার পাঁচশত টাকা পঞ্চাশ পয়সা মাত্র"
            Money("120500.50").to_words('en')  → "One Lakh Twenty Thousand Five Hundred Taka and Fifty Poisha Only"
        """
        amount_str = f"{self._amount:.2f}"
        int_part, dec_part = amount_str.split(".")
        num_int = int(int_part)
        num_dec = int(dec_part)

        lang = lang.lower().strip()
        
        # Currency units metadata for translations
        units_map = {
            "BDT": {"en": ("Taka", "Poisha"), "bn": ("টাকা", "পয়সা")},
            "USD": {"en": ("Dollar", "Cent"), "bn": ("ডলার", "সেন্ট")},
            "EUR": {"en": ("Euro", "Cent"), "bn": ("ইউরো", "সেন্ট")},
            "GBP": {"en": ("Pound", "Penny"), "bn": ("পাউন্ড", "পেনি")},
            "INR": {"en": ("Rupee", "Paise"), "bn": ("রুপি", "পয়সা")},
        }
        
        default_units = {
            "en": (self._currency, "Sub-unit"),
            "bn": (self._currency, "পয়সা")
        }
        
        currency_info = units_map.get(self._currency, default_units)
        main_unit, sub_unit = currency_info[lang] if lang in currency_info else default_units[lang]

        # Singular/Plural adjustments for English
        if lang == "en":
            if num_int != 1 and main_unit in ("Dollar", "Euro", "Pound", "Rupee"):
                main_unit += "s"
            if num_dec != 1 and sub_unit in ("Cent", "Penny", "Paise"):
                if sub_unit == "Penny":
                    sub_unit = "Pence"
                else:
                    sub_unit += "s"

        if lang == "bn":
            words_int = number_to_words(num_int, lang="bn") if num_int > 0 else ""
            words_dec = number_to_words(num_dec, lang="bn") if num_dec > 0 else ""
            
            if num_int == 0 and num_dec == 0:
                return f"শূণ্য {main_unit} মাত্র"
                
            res = ""
            if num_int > 0:
                res += f"{words_int} {main_unit}"
            if num_dec > 0:
                if res:
                    res += f" {words_dec} {sub_unit}"
                else:
                    res += f"{words_dec} {sub_unit}"
            return f"{res} মাত্র"
            
        else:  # english
            if style is None:
                style = "indian" if self._currency in ("BDT", "INR") else "international"
                
            words_int = number_to_words(num_int, lang="en", style=style) if num_int > 0 else ""
            words_dec = number_to_words(num_dec, lang="en", style=style) if num_dec > 0 else ""
            
            if num_int == 0 and num_dec == 0:
                return f"Zero {main_unit} Only"
                
            res = ""
            if num_int > 0:
                res += f"{words_int} {main_unit}"
            if num_dec > 0:
                if res:
                    res += f" and {words_dec} {sub_unit}"
                else:
                    res += f"{words_dec} {sub_unit}"
            return f"{res} Only"

    # ─────────────────── Repr ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"Money('{self._amount} {self._currency}')"

    def __str__(self) -> str:
        return f"{self._amount} {self._currency}"


# ─────────────────────────────── Translation Dictionaries ──────────────────────

_BN_ONES = {
    0: '', 1: 'এক', 2: 'দুই', 3: 'তিন', 4: 'চার', 5: 'পাঁচ', 6: 'ছয়', 7: 'সাত', 8: 'আট', 9: 'নয়',
    10: 'দশ', 11: 'এগারো', 12: 'বারো', 13: 'তেরো', 14: 'চৌদ্দ', 15: 'পনেরো', 16: 'ষোলো', 17: 'সতেরো', 18: 'আঠারো', 19: 'উনিশ',
    20: 'বিশ', 21: 'একুশ', 22: 'বাইশ', 23: 'তেইশ', 24: 'চব্বিশ', 25: 'পঁচিশ', 26: 'ছাব্বিশ', 27: 'সাতাশ', 28: 'আটাশ', 29: 'ঊনত্রিশ',
    30: 'ত্রিশ', 31: 'একত্রিশ', 32: 'বত্রিশ', 33: 'তেত্রিশ', 34: 'চৌত্রিশ', 35: 'পঁয়ত্রিশ', 36: 'ছত্রিশ', 37: 'সাঁইত্রিশ', 38: 'আটত্রিশ', 39: 'ঊনচল্লিশ',
    40: 'চল্লিশ', 41: 'একচল্লিশ', 42: 'বিয়াল্লিশ', 43: 'তেতাল্লিশ', 44: 'চৌয়াল্লিশ', 45: 'পঁয়তাল্লিশ', 46: 'ছেচল্লিশ', 47: 'সাতচল্লিশ', 48: 'আটচল্লিশ', 49: 'ঊনপঞ্চাশ',
    50: 'পঞ্চাশ', 51: 'একান্ন', 52: 'বায়ান্ন', 53: 'তিপ্পান্ন', 54: 'চুয়ান্ন', 55: 'পঞ্চান্ন', 56: 'ছাপ্পান্ন', 57: 'সাতান্ন', 58: 'আটান্ন', 59: 'ঊনষাট',
    60: 'ষাট', 61: 'একষট্টি', 62: 'বাষট্টি', 63: 'তেষট্টি', 64: 'চৌষট্টি', 65: 'পয়ষট্টি', 66: 'ছেষট্টি', 67: 'সাতষট্টি', 68: 'আটষট্টি', 69: 'ঊনসত্তর',
    70: 'সত্তর', 71: 'একাত্তর', 72: 'বাহাত্তর', 73: 'তিয়াত্তর', 74: 'চুয়াত্তর', 75: 'পঁচাত্তর', 76: 'ছিয়াত্তর', 77: 'সাতাত্তর', 78: 'আটাত্তর', 79: 'ঊনআশি',
    80: 'আশি', 81: 'একাশি', 82: 'বিরাশি', 83: 'তিরাশি', 84: 'চুরাশি', 85: 'পঁচাশি', 86: 'ছিয়াশি', 87: 'সাতাশি', 88: 'আটাশি', 89: 'ঊননব্বই',
    90: 'নব্বই', 91: 'একানব্বই', 92: 'বিরানব্বই', 93: 'তিরানব্বই', 94: 'চুরানব্বই', 95: 'পঁচানব্বই', 96: 'ছিয়ানব্বই', 97: 'সাতানব্বই', 98: 'আটানব্বই', 99: 'নিরানব্বই'
}

_EN_ONES = {
    0: "", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine",
    10: "Ten", 11: "Eleven", 12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen", 16: "Sixteen",
    17: "Seventeen", 18: "Eighteen", 19: "Nineteen"
}

_EN_TENS = {
    2: "Twenty", 3: "Thirty", 4: "Forty", 5: "Fifty", 6: "Sixty", 7: "Seventy", 8: "Eighty", 9: "Ninety"
}


# ─────────────────────────────── Integer to Words Converters ───────────────────

def _integer_to_words_bn(n: int) -> str:
    """নিজে নিজে রিকার্সিভলি ধনাত্মক সংখ্যাকে বাংলায় লেখে"""
    if n == 0:
        return ""
    if n < 100:
        return _BN_ONES[n]
    elif n < 1000:
        hundreds = n // 100
        hundreds_word = _BN_ONES[hundreds] + "শত"
        rem = _integer_to_words_bn(n % 100)
        return f"{hundreds_word} {rem}".strip()
    elif n < 100000:  # Thousand
        thousands = _integer_to_words_bn(n // 1000) + " হাজার"
        rem = _integer_to_words_bn(n % 1000)
        return f"{thousands} {rem}".strip()
    elif n < 10000000:  # Lakh
        lakhs = _integer_to_words_bn(n // 100000) + " লক্ষ"
        rem = _integer_to_words_bn(n % 100000)
        return f"{lakhs} {rem}".strip()
    else:  # Crore
        crores = _integer_to_words_bn(n // 10000000) + " কোটি"
        rem = _integer_to_words_bn(n % 10000000)
        return f"{crores} {rem}".strip()


def _integer_to_words_en_intl(n: int) -> str:
    """International style (Thousand, Million, Billion)"""
    if n == 0:
        return ""
    if n < 20:
        return _EN_ONES[n]
    elif n < 100:
        tens = _EN_TENS[n // 10]
        ones = _EN_ONES[n % 10]
        return f"{tens}-{ones}" if ones else tens
    elif n < 1000:
        hundreds = _EN_ONES[n // 100] + " Hundred"
        rem = _integer_to_words_en_intl(n % 100)
        return f"{hundreds} and {rem}" if rem else hundreds
    elif n < 1000000:
        thousands = _integer_to_words_en_intl(n // 1000) + " Thousand"
        rem = _integer_to_words_en_intl(n % 1000)
        return f"{thousands}, {rem}" if rem else thousands
    elif n < 1000000000:
        millions = _integer_to_words_en_intl(n // 1000000) + " Million"
        rem = _integer_to_words_en_intl(n % 1000000)
        return f"{millions}, {rem}" if rem else millions
    else:
        billions = _integer_to_words_en_intl(n // 1000000000) + " Billion"
        rem = _integer_to_words_en_intl(n % 1000000000)
        return f"{billions}, {rem}" if rem else billions


def _integer_to_words_en_indian(n: int) -> str:
    """South Asian style (Thousand, Lakh, Crore)"""
    if n == 0:
        return ""
    if n < 20:
        return _EN_ONES[n]
    elif n < 100:
        tens = _EN_TENS[n // 10]
        ones = _EN_ONES[n % 10]
        return f"{tens}-{ones}" if ones else tens
    elif n < 1000:
        hundreds = _EN_ONES[n // 100] + " Hundred"
        rem = _integer_to_words_en_indian(n % 100)
        return f"{hundreds} and {rem}" if rem else hundreds
    elif n < 100000:
        thousands = _integer_to_words_en_indian(n // 1000) + " Thousand"
        rem = _integer_to_words_en_indian(n % 1000)
        return f"{thousands}, {rem}" if rem else thousands
    elif n < 10000000:
        lakhs = _integer_to_words_en_indian(n // 100000) + " Lakh"
        rem = _integer_to_words_en_indian(n % 100000)
        return f"{lakhs}, {rem}" if rem else lakhs
    else:
        crores = _integer_to_words_en_indian(n // 10000000) + " Crore"
        rem = _integer_to_words_en_indian(n % 10000000)
        return f"{crores}, {rem}" if rem else crores


def number_to_words(number: Numeric, lang: str = "bn", style: str = "indian") -> str:
    """
    যেকোনো সংখ্যাকে কথায় রূপান্তর করে (বাংলা/ইংরেজি)।
    
    Args:
        number: int, float, Decimal বা Money
        lang:   'bn' বা 'en'
        style:  'indian' (Lakh/Crore) বা 'international' (Million/Billion)
        
    উদাহরণ:
        number_to_words(120500, lang='bn')  → "এক লক্ষ বিশ হাজার পাঁচশত"
        number_to_words(120500, lang='en')  → "One Lakh Twenty Thousand Five Hundred"
    """
    if isinstance(number, Money):
        return number.to_words(lang=lang, style=style)
        
    try:
        val = int(math.floor(float(number)))
    except (ValueError, TypeError):
        raise MoneyError(f"কথায় রূপান্তরের জন্য সংখ্যাটি অবৈধ: {number}")
        
    lang = lang.lower().strip()
    
    if val == 0:
        return "শূণ্য" if lang == "bn" else "Zero"
        
    prefix = ""
    if val < 0:
        prefix = "মাইনাস " if lang == "bn" else "Minus "
        val = abs(val)
        
    if lang == "bn":
        return prefix + _integer_to_words_bn(val)
    else:
        if style == "indian":
            return prefix + _integer_to_words_en_indian(val)
        return prefix + _integer_to_words_en_intl(val)


# ─────────────────────────────── Helper Functions ─────────────────────────────

def money(amount: Numeric = 0, currency: str | None = None) -> Money:
    """
    Money তৈরির shorthand।

    উদাহরণ:
        price = money(1500)          # Money('1500.00 BDT')
        tax   = money("225.50")      # Money('225.50 BDT')
    """
    return Money(amount, currency)


def zero(currency: str | None = None) -> Money:
    """শূন্য Money তৈরি করা"""
    return Money(0, currency)


def percent_of(amount: Money, rate: Union[int, float, str, Decimal]) -> Money:
    """
    একটি পরিমাণের নির্দিষ্ট শতাংশ বের করা।

    উদাহরণ:
        price  = Money(10000)
        vat    = percent_of(price, 15)    # 1500.00 BDT (১৫% ভ্যাট)
        disc   = percent_of(price, 10)    # 1000.00 BDT (১০% ছাড়)
        net    = price - disc             # 9000.00 BDT
        total  = net + percent_of(net, 15)  # 10350.00 BDT
    """
    rate_decimal = Decimal(str(rate)) / Decimal("100")
    return amount * rate_decimal


def split_amount(
    amount: Money,
    parts: int,
    rounding: str = "up",
) -> list[Money]:
    """
    একটি পরিমাণ সমান ভাগে বিভক্ত করা।
    বাকি অংশ শেষ ভাগে যোগ হয় (penny distribution)।

    ব্যবহার: কিস্তিতে ঋণ পরিশোধ, installment calculation

    উদাহরণ:
        total  = Money(1000)
        parts  = split_amount(total, 3)
        # [Money('333.34 BDT'), Money('333.33 BDT'), Money('333.33 BDT')]
        # যোগফল = 1000.00 (সঠিক!)
    """
    if parts <= 0:
        raise MoneyError(f"ভাগের সংখ্যা ধনাত্মক হতে হবে, পেলাম: {parts}")

    quant   = Decimal(10) ** -Money.DECIMAL_PLACES
    each    = (amount.amount / Decimal(str(parts))).quantize(quant, rounding=ROUND_HALF_UP)
    total   = each * Decimal(str(parts))
    diff    = amount.amount - total  # rounding-এর কারণে পার্থক্য

    result  = [Money(each, amount.currency) for _ in range(parts)]
    # পার্থক্য প্রথম ভাগে যোগ (বা শেষ ভাগে — ব্যবসায়িক নিয়ম অনুযায়ী)
    result[0] = Money(each + diff, amount.currency)
    return result


def sum_money(amounts: list[Money], currency: str | None = None) -> Money:
    """
    Money-র তালিকার যোগফল।

    উদাহরণ:
        items = [Money(500), Money(300), Money(200)]
        total = sum_money(items)   # Money('1000.00 BDT')
    """
    if not amounts:
        return zero(currency)
    result = amounts[0]
    for m in amounts[1:]:
        result = result + m
    return result


def apply_tax(
    amount: Money,
    tax_rate: Union[int, float, str, Decimal],
    inclusive: bool = False,
) -> tuple[Money, Money, Money]:
    """
    ট্যাক্স হিসাব করা।

    Args:
        amount:    মূল পরিমাণ
        tax_rate:  ট্যাক্সের হার (%, যেমন 15 মানে ১৫%)
        inclusive: True = ট্যাক্স ইতিমধ্যে পরিমাণের ভেতরে আছে

    Returns:
        (base_amount, tax_amount, total_amount)

    উদাহরণ:
        # Exclusive (ট্যাক্স বাইরে):
        base, tax, total = apply_tax(Money(10000), 15)
        # base=10000, tax=1500, total=11500

        # Inclusive (ট্যাক্স ভেতরে):
        base, tax, total = apply_tax(Money(11500), 15, inclusive=True)
        # base=10000, tax=1500, total=11500
    """
    rate = Decimal(str(tax_rate)) / Decimal("100")

    if inclusive:
        # total থেকে base বের করা: base = total / (1 + rate)
        base  = amount / (Decimal("1") + rate)
        tax   = amount - base
        total = amount
    else:
        base  = amount
        tax   = amount * rate
        total = amount + tax

    return base, tax, total


def exchange(
    amount: Money,
    rate: Union[int, float, str, Decimal],
    target_currency: str,
) -> Money:
    """
    মুদ্রা রূপান্তর।

    উদাহরণ:
        usd = Money(100, "USD")
        bdt = exchange(usd, 110, "BDT")   # Money('11000.00 BDT')
    """
    converted = amount.amount * Decimal(str(rate))
    return Money(converted, target_currency)


def max_money(*amounts: Money) -> Money:
    """সর্বোচ্চ Money পরিমাণ"""
    if not amounts:
        raise MoneyError("কমপক্ষে একটি পরিমাণ দিতে হবে")
    result = amounts[0]
    for m in amounts[1:]:
        if m > result:
            result = m
    return result


def min_money(*amounts: Money) -> Money:
    """সর্বনিম্ন Money পরিমাণ"""
    if not amounts:
        raise MoneyError("কমপক্ষে একটি পরিমাণ দিতে হবে")
    result = amounts[0]
    for m in amounts[1:]:
        if m < result:
            result = m
    return result
