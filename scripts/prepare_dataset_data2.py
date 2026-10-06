"""
Script to prepare and format Data2 dataset for YOLO training.
Converts COCO format annotations into YOLO txt format and
organizes the data into train/valid/test splits with data.yaml.
"""

import os
import json
import shutil
import random

def prepare_data2():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data2"))
    train_source_dir = os.path.join(base_dir, "train")
    coco_json_path = os.path.join(train_source_dir, "_annotations.coco.json")

    if not os.path.exists(coco_json_path):
        print(f"Error: COCO annotations not found at {coco_json_path}")
        return False

    print(f"[1/5] Loading COCO annotations from: {coco_json_path}")
    with open(coco_json_path, "r", encoding="utf-8") as f:
        coco_data = json.load(f)

    images = coco_data.get("images", [])
    annotations = coco_data.get("annotations", [])
    categories = coco_data.get("categories", [])

    print(f"      Total images: {len(images)}")
    print(f"      Total annotations: {len(annotations)}")
    print(f"      Categories: {categories}")

    # Map categories: Category 1 ('arrow') -> 0, Category 2 ('impact') -> 1
    # Category 0 ('objects') is unannotated
    cat_map = {1: 0, 2: 1}
    class_names = ["arrow", "impact"]

    # Group annotations by image_id
    ann_by_image = {}
    for ann in annotations:
        img_id = ann["image_id"]
        if img_id not in ann_by_image:
            ann_by_image[img_id] = []
        ann_by_image[img_id].append(ann)

    # Random split with fixed seed
    random.seed(42)
    shuffled_images = list(images)
    random.shuffle(shuffled_images)

    total = len(shuffled_images)
    train_count = int(total * 0.80)   # 160 images (80%)
    val_count = int(total * 0.15)     # 30 images (15%)
    test_count = total - train_count - val_count  # 10 images (5%)

    splits = {
        "train": shuffled_images[:train_count],
        "valid": shuffled_images[train_count:train_count + val_count],
        "test": shuffled_images[train_count + val_count:]
    }

    print(f"[2/5] Splitting dataset:")
    print(f"      - Train: {len(splits['train'])} images")
    print(f"      - Valid: {len(splits['valid'])} images")
    print(f"      - Test:  {len(splits['test'])} images")

    # Destination directories
    temp_dir = os.path.join(base_dir, "_temp_splits")
    os.makedirs(temp_dir, exist_ok=True)

    stats = {"arrow": 0, "impact": 0}

    print("[3/5] Converting COCO bounding boxes to YOLO format...")
    for split_name, img_list in splits.items():
        img_dest_dir = os.path.join(temp_dir, split_name, "images")
        lbl_dest_dir = os.path.join(temp_dir, split_name, "labels")
        os.makedirs(img_dest_dir, exist_ok=True)
        os.makedirs(lbl_dest_dir, exist_ok=True)

        for img_info in img_list:
            img_id = img_info["id"]
            file_name = img_info["file_name"]
            img_w = float(img_info["width"])
            img_h = float(img_info["height"])

            src_img_path = os.path.join(train_source_dir, file_name)
            dst_img_path = os.path.join(img_dest_dir, file_name)

            if os.path.exists(src_img_path):
                shutil.copy2(src_img_path, dst_img_path)

            # Process labels
            yolo_lines = []
            img_anns = ann_by_image.get(img_id, [])
            for ann in img_anns:
                cat_id = ann["category_id"]
                if cat_id not in cat_map:
                    continue

                yolo_cls = cat_map[cat_id]
                cls_name = class_names[yolo_cls]
                stats[cls_name] += 1

                # COCO bbox: [x_min, y_min, width, height]
                bbox = ann["bbox"]
                x_min, y_min, bw, bh = bbox[0], bbox[1], bbox[2], bbox[3]

                # Convert to normalized center x, center y, width, height
                x_c = (x_min + bw / 2.0) / img_w
                y_c = (y_min + bh / 2.0) / img_h
                w_norm = bw / img_w
                h_norm = bh / img_h

                # Clamp to [0.0, 1.0]
                x_c = max(0.0, min(1.0, x_c))
                y_c = max(0.0, min(1.0, y_c))
                w_norm = max(0.0, min(1.0, w_norm))
                h_norm = max(0.0, min(1.0, h_norm))

                yolo_lines.append(f"{yolo_cls} {x_c:.6f} {y_c:.6f} {w_norm:.6f} {h_norm:.6f}\n")

            txt_name = os.path.splitext(file_name)[0] + ".txt"
            dst_lbl_path = os.path.join(lbl_dest_dir, txt_name)
            with open(dst_lbl_path, "w", encoding="utf-8") as f:
                f.writelines(yolo_lines)

    print(f"      Total converted instances: {stats}")

    print("[4/5] Finalizing folder structure in Data2...")
    # Clean up train_source_dir or replace with split
    backup_coco = os.path.join(base_dir, "_annotations.coco.json.bak")
    if os.path.exists(coco_json_path):
        shutil.copy2(coco_json_path, backup_coco)

    # Move splits into place
    for split_name in ["train", "valid", "test"]:
        final_split_dir = os.path.join(base_dir, split_name)
        if os.path.exists(final_split_dir):
            shutil.rmtree(final_split_dir)
        shutil.move(os.path.join(temp_dir, split_name), final_split_dir)

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    print("[5/5] Generating data.yaml...")
    yaml_content = f"""train: ../Data2/train/images
val: ../Data2/valid/images
test: ../Data2/test/images

nc: 2
names: ['arrow', 'impact']

roboflow:
  workspace: archer-a8cas
  project: my-first-project
  version: 2
  license: CC BY 4.0
"""
    data_yaml_path = os.path.join(base_dir, "data.yaml")
    with open(data_yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"\n[SUCCESS] Data2 dataset prepared successfully at {base_dir}!")
    print(f"          Configuration: {data_yaml_path}")
    print(f"          Classes (nc=2): {class_names}")
    return True

if __name__ == "__main__":
    prepare_data2()
