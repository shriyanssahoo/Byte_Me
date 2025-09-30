import pandas as pd

def load_classes(file_path="data/classes.csv"):
    df = pd.read_csv(file_path)
    return df

def generate_timetable(df):
    # For now, just return input as "scheduled"
    return df

if __name__ == "__main__":
    classes = load_classes()
    timetable = generate_timetable(classes)
    print("Generated Timetable:")
    print(timetable)
