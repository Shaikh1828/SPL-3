"""
Script to clean and standardize the dataset labels by converting multi-point polygon annotations
into strict 5-value YOLO bounding boxes (class, x_center, y_center, width, height).
"""

import os
import glob

def convert_label_file(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()
        
    converted_lines = []
    converted_count = 0
    
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
            
        cls = parts[0]
        coords = [float(p) for p in parts[1:]]
        
        if len(coords) == 4:
            # Already a 4-coordinate bounding box (x_center, y_center, width, height)
            converted_lines.append(f"{cls} {' '.join(parts[1:])}\n")
        elif len(coords) > 4:
            # Polygon coordinates: x1, y1, x2, y2, ...
            xs = coords[0::2]
            ys = coords[1::2]
            
            xmin = max(0.0, min(xs))
            xmax = min(1.0, max(xs))
            ymin = max(0.0, min(ys))
            ymax = min(1.0, max(ys))
            
            xc = (xmin + xmax) / 2.0
            yc = (ymin + ymax) / 2.0
            w = xmax - xmin
            h = ymax - ymin
            
            converted_lines.append(f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
            converted_count += 1
            
    with open(file_path, "w") as f:
        f.writelines(converted_lines)
        
    return len(lines), converted_count

def process_split(split_name, data_dir):
    labels_dir = os.path.join(data_dir, split_name, "labels")
    if not os.path.exists(labels_dir):
        print(f"Directory not found: {labels_dir}")
        return
        
    txt_files = glob.glob(os.path.join(labels_dir, "*.txt"))
    total_files = len(txt_files)
    total_instances = 0
    total_converted = 0
    
    for txt_file in txt_files:
        lines_cnt, conv_cnt = convert_label_file(txt_file)
        total_instances += lines_cnt
        total_converted += conv_cnt
        
    print(f"[{split_name.upper()}] Processed {total_files} files, {total_instances} total instances. Converted {total_converted} polygon instances to bboxes.")

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data"))
    print(f"Cleaning label annotations in: {base_dir}")
    
    for split in ["train", "valid", "test"]:
        process_split(split, base_dir)
        
    print("\nDataset preparation completed successfully! All labels are now standardized 5-value bounding boxes.")

if __name__ == "__main__":
    main()
