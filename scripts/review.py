#!/usr/bin/env python3
import sys
import csv
import gzip
import base64
from pathlib import Path

def save_review(image_path, comment, script_path, csv_path="reviews.csv"):
    """Save image review with compressed source code to CSV"""

    # Read and compress source code
    with open(script_path, 'rb') as f:
        source_code = f.read()
    compressed = gzip.compress(source_code)
    encoded = base64.b64encode(compressed).decode('utf-8')

    # Check if CSV exists
    csv_file = Path(csv_path)
    file_exists = csv_file.exists()

    # Write to CSV
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['image_path', 'comment', 'source_code_b64gz', 'script_name'])
        writer.writerow([image_path, comment, encoded, Path(script_path).name])

    print(f"Review saved for {image_path}")

def load_review(csv_path="reviews.csv", row_number=None):
    """Load review from CSV and optionally extract source code"""

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        if row_number is not None:
            if 0 <= row_number < len(rows):
                row = rows[row_number]
                # Decompress source code
                encoded = row['source_code_b64gz']
                compressed = base64.b64decode(encoded)
                source_code = gzip.decompress(compressed).decode('utf-8')
                return {
                    'image_path': row['image_path'],
                    'comment': row['comment'],
                    'source_code': source_code,
                    'script_name': row['script_name']
                }
            else:
                print(f"Row {row_number} out of range")
                return None
        else:
            # Return all reviews
            return rows

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Save: python review.py save <image_path> <comment> <script_path>")
        print("  Load: python review.py load <csv_path> [row_number]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) != 5:
            print("Usage: python review.py save <image_path> <comment> <script_path>")
            sys.exit(1)
        save_review(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "load":
        if len(sys.argv) < 3:
            print("Usage: python review.py load <csv_path> [row_number]")
            sys.exit(1)

        csv_path = sys.argv[2]
        row_num = int(sys.argv[3]) if len(sys.argv) > 3 else None

        result = load_review(csv_path, row_num)

        if row_num is not None and result:
            print(f"Image: {result['image_path']}")
            print(f"Comment: {result['comment']}")
            print(f"Script: {result['script_name']}")
            print(f"\nSource code:\n{result['source_code']}")
        else:
            for i, row in enumerate(result):
                print(f"{i}: {row['image_path']} - {row['comment']}")
