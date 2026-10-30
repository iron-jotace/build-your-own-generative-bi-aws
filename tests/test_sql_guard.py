\
import unittest

from src.sql_guard import SQLValidationError, validate_sql


class SQLGuardTests(unittest.TestCase):
    VIEW = "vw_nexa_genbi_sales"

    def test_valid_select(self):
        sql = """
        SELECT category, SUM(revenue) AS revenue
        FROM vw_nexa_genbi_sales
        GROUP BY category
        """
        self.assertTrue(validate_sql(sql, self.VIEW))

    def test_blocks_other_table(self):
        with self.assertRaises(SQLValidationError):
            validate_sql("SELECT order_id FROM fact_sales", self.VIEW)

    def test_blocks_select_star(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "SELECT * FROM vw_nexa_genbi_sales",
                self.VIEW,
            )

    def test_blocks_delete(self):
        with self.assertRaises(SQLValidationError):
            validate_sql(
                "DELETE FROM vw_nexa_genbi_sales",
                self.VIEW,
            )


if __name__ == "__main__":
    unittest.main()
