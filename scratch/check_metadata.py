import joblib
metadata = joblib.load(r"c:\Users\HP\OneDrive\Desktop\Aegis AI-II\models\pretrained\tasks_metadata.pkl")
print(f"Total tasks: {len(metadata)}")
if metadata:
    print(f"Sample keys: {list(metadata[0].keys())}")
    print(f"Sample data: {metadata[0]}")
