"""
tests/test_decimal_math.py
===========================
Money class এবং সব helper function-এর unit test।
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from decimal import Decimal
from core.decimal_math import (
    Money, money, zero,
    percent_of, split_amount, sum_money,
    apply_tax, exchange,
    max_money, min_money,
    MoneyError, CurrencyMismatchError,
)


class MoneyCreationTest(unittest.TestCase):

    def test_int_input(self):
        m = Money(1500)
        self.assertEqual(m.amount, Decimal("1500.00"))

    def test_float_input_rounds_correctly(self):
        """float input সঠিকভাবে গোল হওয়া উচিত"""
        m = Money(0.1)
        self.assertEqual(m.amount, Decimal("0.10"))

    def test_string_input(self):
        m = Money("1725.50")
        self.assertEqual(m.amount, Decimal("1725.50"))

    def test_decimal_input(self):
        m = Money(Decimal("999.99"))
        self.assertEqual(m.amount, Decimal("999.99"))

    def test_default_currency_is_bdt(self):
        m = Money(100)
        self.assertEqual(m.currency, "BDT")

    def test_custom_currency(self):
        m = Money(100, "USD")
        self.assertEqual(m.currency, "USD")

    def test_currency_uppercased(self):
        m = Money(100, "usd")
        self.assertEqual(m.currency, "USD")

    def test_rounding_half_up(self):
        """0.005 → 0.01 হওয়া উচিত (ROUND_HALF_UP)"""
        m = Money("0.005")
        self.assertEqual(m.amount, Decimal("0.01"))

    def test_zero_money(self):
        m = Money(0)
        self.assertTrue(m.is_zero)
        self.assertFalse(m.is_positive)

    def test_negative_money(self):
        m = Money(-500)
        self.assertTrue(m.is_negative)
        self.assertFalse(m.is_positive)

    def test_invalid_input_raises_error(self):
        with self.assertRaises(MoneyError):
            Money("abc")


class MoneyArithmeticTest(unittest.TestCase):
    """সব arithmetic operator test"""

    def test_add_two_money(self):
        result = Money(100) + Money(200)
        self.assertEqual(result, Money(300))

    def test_float_precision_not_lost(self):
        """বিখ্যাত float সমস্যা: 0.1 + 0.2 ≠ 0.3"""
        result = Money("0.1") + Money("0.2")
        self.assertEqual(result, Money("0.3"))  # Money দিয়ে সঠিক!

    def test_add_number(self):
        result = Money(100) + 50
        self.assertEqual(result, Money(150))

    def test_radd_for_sum(self):
        """sum() function-এ ব্যবহার করার জন্য"""
        amounts = [Money(100), Money(200), Money(300)]
        self.assertEqual(sum(amounts), Money(600))

    def test_subtract_money(self):
        result = Money(500) - Money(200)
        self.assertEqual(result, Money(300))

    def test_multiply_by_decimal(self):
        result = Money(1000) * Decimal("0.15")
        self.assertEqual(result, Money(150))

    def test_multiply_by_int(self):
        result = Money(100) * 3
        self.assertEqual(result, Money(300))

    def test_divide_by_number(self):
        result = Money(300) / 3
        self.assertEqual(result, Money(100))

    def test_divide_by_zero_raises(self):
        with self.assertRaises(MoneyError):
            Money(100) / 0

    def test_negate(self):
        result = -Money(500)
        self.assertEqual(result, Money(-500))

    def test_abs(self):
        result = abs(Money(-500))
        self.assertEqual(result, Money(500))

    def test_currency_mismatch_raises(self):
        with self.assertRaises(CurrencyMismatchError):
            Money(100, "BDT") + Money(100, "USD")

    def test_money_times_money_raises(self):
        with self.assertRaises(MoneyError):
            Money(100) * Money(2)


class MoneyComparisonTest(unittest.TestCase):

    def test_equal(self):
        self.assertEqual(Money(100), Money(100))

    def test_not_equal_different_amount(self):
        self.assertNotEqual(Money(100), Money(200))

    def test_not_equal_different_currency(self):
        self.assertNotEqual(Money(100, "BDT"), Money(100, "USD"))

    def test_less_than(self):
        self.assertTrue(Money(100) < Money(200))

    def test_greater_than(self):
        self.assertTrue(Money(300) > Money(200))

    def test_less_than_or_equal(self):
        self.assertTrue(Money(100) <= Money(100))
        self.assertTrue(Money(100) <= Money(200))

    def test_bool_true_when_nonzero(self):
        self.assertTrue(bool(Money(100)))

    def test_bool_false_when_zero(self):
        self.assertFalse(bool(Money(0)))


class MoneyDatabaseTest(unittest.TestCase):

    def test_to_paisa(self):
        """১,৭২৫.৫০ টাকা = ১,৭২,৫৫০ পয়সা"""
        m = Money("1725.50")
        self.assertEqual(m.to_paisa(), 172550)

    def test_from_paisa(self):
        m = Money.from_paisa(172550)
        self.assertEqual(m, Money("1725.50"))

    def test_paisa_roundtrip(self):
        original = Money("9999.99")
        restored = Money.from_paisa(original.to_paisa())
        self.assertEqual(original, restored)

    def test_to_decimal(self):
        m = Money("100.50")
        self.assertIsInstance(m.to_decimal(), Decimal)
        self.assertEqual(m.to_decimal(), Decimal("100.50"))

    def test_to_str(self):
        self.assertEqual(Money("1500.00").to_str(), "1500.00")


class MoneyFormattingTest(unittest.TestCase):

    def test_basic_format(self):
        result = Money(1725500).format()
        self.assertEqual(result, "1,725,500.00")

    def test_format_with_symbol_bdt(self):
        result = Money(1000).format(symbol=True)
        self.assertEqual(result, "৳ 1,000.00")

    def test_format_with_symbol_usd(self):
        result = Money(1000, "USD").format(symbol=True)
        self.assertEqual(result, "$ 1,000.00")

    def test_format_negative(self):
        result = Money(-500).format()
        self.assertEqual(result, "-500.00")

    def test_format_bangla_digits(self):
        result = Money(1500).format(bangla_digits=True)
        # ১,৫০০.০০
        self.assertIn("১", result)
        self.assertIn("৫", result)

    def test_repr(self):
        self.assertIn("Money", repr(Money(100)))
        self.assertIn("BDT", repr(Money(100)))


class HelperFunctionTest(unittest.TestCase):

    def test_money_shorthand(self):
        m = money(500)
        self.assertIsInstance(m, Money)
        self.assertEqual(m, Money(500))

    def test_zero_function(self):
        m = zero()
        self.assertTrue(m.is_zero)

    def test_percent_of(self):
        """১০,০০০ টাকার ১৫% = ১,৫০০"""
        result = percent_of(Money(10000), 15)
        self.assertEqual(result, Money(1500))

    def test_percent_of_decimal_rate(self):
        """১০,০০০ টাকার ৭.৫% = ৭৫০"""
        result = percent_of(Money(10000), "7.5")
        self.assertEqual(result, Money(750))

    def test_split_amount_even(self):
        """১,০০০ টাকা ৪ ভাগে = ২৫০ × ৪"""
        parts = split_amount(Money(1000), 4)
        self.assertEqual(len(parts), 4)
        self.assertEqual(sum(parts), Money(1000))
        self.assertTrue(all(p == Money(250) for p in parts))

    def test_split_amount_uneven(self):
        """১,০০০ টাকা ৩ ভাগে — যোগফল অবশ্যই মিলতে হবে"""
        parts = split_amount(Money(1000), 3)
        self.assertEqual(len(parts), 3)
        self.assertEqual(sum(parts), Money(1000))

    def test_split_amount_invalid(self):
        with self.assertRaises(MoneyError):
            split_amount(Money(1000), 0)

    def test_sum_money(self):
        items = [Money(100), Money(200), Money(300)]
        self.assertEqual(sum_money(items), Money(600))

    def test_sum_money_empty(self):
        self.assertEqual(sum_money([]), zero())

    def test_apply_tax_exclusive(self):
        """১০,০০০ টাকায় ১৫% ভ্যাট (exclusive)"""
        base, tax, total = apply_tax(Money(10000), 15)
        self.assertEqual(base,  Money(10000))
        self.assertEqual(tax,   Money(1500))
        self.assertEqual(total, Money(11500))

    def test_apply_tax_inclusive(self):
        """১১,৫০০ টাকায় ১৫% ভ্যাট inclusive"""
        base, tax, total = apply_tax(Money("11500"), 15, inclusive=True)
        self.assertEqual(total, Money("11500.00"))
        self.assertEqual(base + tax, total)

    def test_exchange(self):
        """১০০ USD × ১১০ = ১১,০০০ BDT"""
        usd = Money(100, "USD")
        bdt = exchange(usd, 110, "BDT")
        self.assertEqual(bdt, Money(11000, "BDT"))
        self.assertEqual(bdt.currency, "BDT")

    def test_max_money(self):
        self.assertEqual(max_money(Money(100), Money(500), Money(300)), Money(500))

    def test_min_money(self):
        self.assertEqual(min_money(Money(100), Money(500), Money(300)), Money(100))


class AccountingScenarioTest(unittest.TestCase):
    """বাস্তব accounting scenario test"""

    def test_invoice_calculation(self):
        """
        Invoice:
          পণ্য: ৫,০০০ টাকা
          ছাড়: ১০%
          ভ্যাট: ১৫%
        """
        subtotal = Money(5000)
        discount = percent_of(subtotal, 10)   # 500.00
        after_disc = subtotal - discount        # 4500.00
        vat = percent_of(after_disc, 15)        # 675.00
        total = after_disc + vat                # 5175.00

        self.assertEqual(discount,   Money(500))
        self.assertEqual(after_disc, Money(4500))
        self.assertEqual(vat,        Money(675))
        self.assertEqual(total,      Money(5175))

    def test_installment_plan(self):
        """
        ঋণ: ১০,০০০ টাকা, ৩ কিস্তিতে
        মোট কিস্তি অবশ্যই মূল পরিমাণের সমান
        """
        loan = Money(10000)
        installments = split_amount(loan, 3)

        self.assertEqual(sum(installments), loan)
        self.assertEqual(len(installments), 3)

    def test_payroll_deduction(self):
        """
        বেতন: ৩০,০০০
        আয়কর: ৫%
        PF: ১০%
        নেট বেতন হিসাব
        """
        gross = Money(30000)
        income_tax = percent_of(gross, 5)     # 1500.00
        pf = percent_of(gross, 10)             # 3000.00
        total_deduction = income_tax + pf      # 4500.00
        net = gross - total_deduction          # 25500.00

        self.assertEqual(income_tax,      Money(1500))
        self.assertEqual(pf,              Money(3000))
        self.assertEqual(total_deduction, Money(4500))
        self.assertEqual(net,             Money(25500))

    def test_vat_inclusive_breakdown(self):
        """
        রসিদে ভ্যাট-সহ মূল্য দেওয়া আছে: ১১,৫০০ টাকা (১৫% ভ্যাট inclusive)
        Actual price ও VAT amount বের করা
        """
        total_with_vat = Money("11500")
        base, vat, total = apply_tax(total_with_vat, 15, inclusive=True)

        # Base + VAT = Total (সর্বদা)
        self.assertEqual(base + vat, total)

    def test_database_storage_precision(self):
        """
        Database-এ পয়সায় সংরক্ষণ করলেও নির্ভুলতা বজায় থাকে
        """
        original = Money("99999.99")
        paisa    = original.to_paisa()       # 9999999
        restored = Money.from_paisa(paisa)   # 99999.99

        self.assertEqual(original, restored)
        self.assertEqual(paisa, 9999999)


class MoneyToWordsTest(unittest.TestCase):

    def test_bangla_to_words_basic(self):
        m = Money("1250.50", "BDT")
        self.assertEqual(m.to_words("bn"), "এক হাজার দুইশত পঞ্চাশ টাকা পঞ্চাশ পয়সা মাত্র")

    def test_english_indian_style_words(self):
        m = Money("120500.25", "BDT")
        self.assertEqual(m.to_words("en", style="indian"), "One Lakh, Twenty Thousand, Five Hundred Taka and Twenty-Five Poisha Only")

    def test_english_intl_style_words(self):
        m = Money("120500.25", "USD")
        self.assertEqual(m.to_words("en", style="international"), "One Hundred and Twenty Thousand, Five Hundred Dollars and Twenty-Five Cents Only")

    def test_global_helper_number_to_words(self):
        from core.decimal_math import number_to_words
        self.assertEqual(number_to_words(12500000, lang="bn"), "এক কোটি পঁচিশ লক্ষ")
        self.assertEqual(number_to_words(12500000, lang="en", style="indian"), "One Crore, Twenty-Five Lakh")
        self.assertEqual(number_to_words(12500000, lang="en", style="international"), "Twelve Million, Five Hundred Thousand")
        self.assertEqual(number_to_words(-500, lang="bn"), "মাইনাস পাঁচশত")
        self.assertEqual(number_to_words(0, lang="bn"), "শূণ্য")


if __name__ == "__main__":
    unittest.main(verbosity=2)
