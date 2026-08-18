import os
import glob
from pathlib import Path
import pandas as pd


def load_initial_stock(stock_dir: str) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Загружает базовый (самый ранний) файл начальных остатков."""
    stock_files = sorted(glob.glob(os.path.join(stock_dir, "stock_*.csv")))
    if not stock_files:
        raise FileNotFoundError(f"В директории '{stock_dir}' не найдены файлы остатков stock_*.csv")

    initial_file = stock_files[0]
    print(f"[INFO] Загрузка начальных остатков из: {initial_file}")

    df_stock = pd.read_csv(
        initial_file,
        sep=";",
        dtype={"item_id": str, "location_id": str},
        parse_dates=["trans_date"]
    )

    df_stock["qty"] = df_stock["qty"].astype(float)
    df_stock["cost_amount"] = df_stock["cost_amount"].astype(float)

    start_date = df_stock["trans_date"].min()
    return df_stock, start_date


def load_all_transactions(trans_dir: str) -> pd.DataFrame:
    """Загружает и объединяет все файлы товародвижения."""
    trans_files = sorted(glob.glob(os.path.join(trans_dir, "invent_trans_*.csv")))
    if not trans_files:
        raise FileNotFoundError(f"В директории '{trans_dir}' не найдены файлы товародвижения invent_trans_*.csv")

    print(f"[INFO] Найдено файлов товародвижения: {len(trans_files)}")

    dfs = []
    for file_path in trans_files:
        df = pd.read_csv(
            file_path,
            sep=";",
            dtype={"item_id": str, "location_id": str},
            parse_dates=["trans_date"]
        )
        df["qty"] = df["qty"].astype(float)
        df["cost_amount"] = df["cost_amount"].astype(float)
        dfs.append(df)

    df_all = pd.concat(dfs, ignore_index=True)
    return df_all


def process_daily_stocks(
        data_dir: str = ".",
        output_dir: str = "./output_stock"
) -> None:
    """
    Основная функция расчета накопительных подневных остатков.

    :param data_dir: Путь к распакованной папке задания (содержащей stock/ и invent_trans/)
    :param output_dir: Папка для сохранения итоговых файлов остатков
    """
    stock_path = os.path.join(data_dir, "stock")
    trans_path = os.path.join(data_dir, "invent_trans")

    df_initial_stock, start_date = load_initial_stock(stock_path)
    df_trans = load_all_transactions(trans_path)

    daily_trans = (
        df_trans.groupby(["item_id", "location_id", "trans_date"], as_index=False)[["qty", "cost_amount"]]
        .sum()
    )

    end_date = df_trans["trans_date"].max()
    print(f"[INFO] Диапазон расчета остатков: с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}")

    current_balances = df_initial_stock.set_index(["item_id", "location_id"])[["qty", "cost_amount"]]

    os.makedirs(output_dir, exist_ok=True)

    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    for current_date in date_range:
        date_str_iso = current_date.strftime("%Y-%m-%d")
        date_str_file = current_date.strftime("%Y_%m_%d")

        todays_trans = daily_trans[daily_trans["trans_date"] == current_date]

        if not todays_trans.empty:
            trans_indexed = todays_trans.set_index(["item_id", "location_id"])[["qty", "cost_amount"]]
            current_balances = current_balances.add(trans_indexed, fill_value=0)

        snapshot = current_balances.reset_index()
        snapshot["trans_date"] = date_str_iso
        snapshot["qty"] = snapshot["qty"].round(4)
        snapshot["cost_amount"] = snapshot["cost_amount"].round(4)
        snapshot = snapshot[["item_id", "location_id", "trans_date", "qty", "cost_amount"]]
        snapshot.sort_values(by=["item_id", "location_id"], inplace=True)

        out_filename = f"stock_{date_str_file}.csv"
        out_path = os.path.join(output_dir, out_filename)
        snapshot.to_csv(out_path, sep=";", index=False)

    print(f"[SUCCESS] Расчет завершен. Файлы сохранены в директорию: '{output_dir}'")


if __name__ == "__main__":
    process_daily_stocks(data_dir=".", output_dir="./output_stock")