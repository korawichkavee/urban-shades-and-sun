from quickhotpoint2 import get_utci_from_coords
import pandas as pd

if __name__ == "__main__":
    # import original csv
    path = "Bangkok_walkable_1764068610_annotated.csv"
    df = pd.read_csv(path)
    # df["datetime-local"] = pd.to_datetime(df["datetime-local"], utc=False)
    df["datetime-local"] = pd.to_datetime(df["datetime-local"], format="ISO8601", errors="coerce")

    # Prepare result lists
    utci_K_list = []
    utci_C_list = []
    ts_list = []

    for idx, row in df.iterrows():
        lat = row["lat"]
        lon = row["lon"]
        # timestamp = row["datetime-local"]
        timestamp = row["datetime-local"].isoformat()  # robust ISO 8601

        utci_K, utci_C, ts = get_utci_from_coords(lat, lon, timestamp)

        utci_K_list.append(utci_K)
        utci_C_list.append(utci_C)
        ts_list.append(ts)

        print(f"Processed {lat}, {lon} at {timestamp}: UTCI = {utci_C:.2f} °C")

    # Assign results to new columns
    df["utci_K"] = utci_K_list
    df["utci_C"] = utci_C_list
    df["utci_timestamp"] = ts_list  # optional

    # Save updated dataframe
    output_path = path.replace(".csv", "_with_utci.csv")
    df.to_csv(output_path, index=False)

    print(f"\nSaved updated CSV to {output_path}")

        
