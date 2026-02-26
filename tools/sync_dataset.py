import os
import shutil

def sync_folders(train_dir, val_dir):
    # Get set of classes in train
    train_classes = set(d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d)))
    
    # Get set of classes in val
    val_classes = set(d for d in os.listdir(val_dir) if os.path.isdir(os.path.join(val_dir, d)))
    
    # Check for empty folders in train (which caused the "15 classes found" error)
    for cls in train_classes:
        path = os.path.join(train_dir, cls)
        if not os.listdir(path):
            print(f"⚠️ Warning: Train folder '{cls}' is empty. You should add images to it or remove it.")
    
    # Remove classes from val that aren't in train
    removed_count = 0
    for cls in val_classes:
        if cls not in train_classes:
            removed_path = os.path.join(val_dir, cls)
            shutil.rmtree(removed_path)
            removed_count += 1
            
    print(f"✅ Sync complete. Removed {removed_count} folders from {val_dir} that were not in {train_dir}.")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    train_path = os.path.join(project_root, "dataset", "train")
    val_path = os.path.join(project_root, "dataset", "val")
    
    if os.path.exists(train_path) and os.path.exists(val_path):
        sync_folders(train_path, val_path)
    else:
        print("Error: Could not find dataset/train or dataset/val")
