import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts import generate_usage_report as report


class GenerateUsageReportTests(unittest.TestCase):
    def test_aggregates_provider_stats_by_day_and_estimates_known_costs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "data_v4.db"
            con = sqlite3.connect(db_path)
            con.execute(
                """
                CREATE TABLE provider_stats (
                    created_at TEXT,
                    provider_id TEXT,
                    provider_model TEXT,
                    status TEXT,
                    token_input_other INTEGER,
                    token_input_cached INTEGER,
                    token_output INTEGER
                )
                """
            )
            con.executemany(
                """
                INSERT INTO provider_stats VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "2026-05-15 08:00:00",
                        "deepseek/deepseek-v4-flash",
                        "deepseek-v4-flash",
                        "completed",
                        1_000_000,
                        2_000_000,
                        500_000,
                    ),
                    (
                        "2026-05-15 09:00:00",
                        "openai/gpt-5.4-mini",
                        "gpt-5.4-mini",
                        "completed",
                        100_000,
                        200_000,
                        10_000,
                    ),
                    (
                        "2026-05-15 10:00:00",
                        "openai/gpt-5.4-nano",
                        "gpt-5.4-nano",
                        "aborted",
                        10,
                        20,
                        30,
                    ),
                ],
            )
            con.commit()
            con.close()

            rows = report.build_daily_rows(db_path)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["日期"], "2026-05-15")
        self.assertEqual(row["调用次数"], "3")
        self.assertEqual(row["成功调用次数"], "2")
        self.assertEqual(row["异常调用次数"], "1")
        self.assertEqual(row["DeepSeek输入Token"], "1000000")
        self.assertEqual(row["DeepSeek缓存输入Token"], "2000000")
        self.assertEqual(row["DeepSeek输出Token"], "500000")
        self.assertEqual(row["OpenAI输入Token"], "100010")
        self.assertEqual(row["OpenAI缓存输入Token"], "200020")
        self.assertEqual(row["OpenAI输出Token"], "10030")
        self.assertEqual(row["估算DeepSeek费用USD"], "0.285600")
        self.assertEqual(row["估算OpenAI费用USD"], "0.135000")
        self.assertIn("openai/gpt-5.4-nano", row["备注"])


if __name__ == "__main__":
    unittest.main()
