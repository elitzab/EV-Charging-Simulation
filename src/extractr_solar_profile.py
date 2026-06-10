import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))

input_path = os.path.join(script_dir, '..', 'data', 'avg_hourly_all_panels_combined.csv')
output_path = os.path.join(script_dir, '..', 'data', 'seasonal_solar_profile_per_panel.csv')


def month_to_season(month):
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"


df = pd.read_csv(input_path)

# getting the solar output for one panel
df["W_per_panel"] = df["avg_W_7panels"] / 7

df["season"] = df["month"].apply(month_to_season)

# averaging over all days in the same season and hour
seasonal = (
    df.groupby(["season", "hour"])["W_per_panel"]
    .mean()
    .reset_index()
)

seasonal["kW_per_panel"] = seasonal["W_per_panel"] / 1000

seasonal.to_csv(output_path, index=False)

print(seasonal)
print(f"Saved to {output_path}")