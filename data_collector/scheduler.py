"""定时数据更新调度器"""

import time
import logging
from datetime import datetime, timedelta, timezone

import schedule

import config
from collector import DataCollector

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            config.LOG_PATH, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger(__name__)


def update_data():
    """执行一次增量数据更新"""
    logger.info("=" * 60)
    logger.info("开始定时数据更新")

    end_time = datetime.now(timezone.utc)
    # 回溯14天，确保覆盖任何遗漏（断点续传会自动跳过已有数据）
    start_time = end_time - timedelta(days=14)

    collector = DataCollector(start_time=start_time, end_time=end_time)
    try:
        collector.run()
        logger.info("定时更新完成")
    except Exception:
        logger.exception("定时更新出错")
    finally:
        collector.close()


def main():
    day = config.SCHEDULE_DAY
    time_str = config.SCHEDULE_TIME

    logger.info(f"调度器启动，计划: 每周{day} {time_str} (UTC) 执行数据更新")
    logger.info(f"币种数: {len(config.SYMBOLS)}，周期: {config.INTERVALS}")

    # 注册定时任务
    getattr(schedule.every(), day).at(time_str).do(update_data)

    # 启动时先执行一次
    logger.info("首次启动，立即执行一次更新...")
    update_data()

    logger.info("进入调度循环，等待下次执行...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
