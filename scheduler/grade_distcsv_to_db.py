import csv
import django
import os
import environ
from django.db import transaction
from typing import List, Dict, Any

import sys
sys.path.append('C:/Users/brenn/VSCode Projects/Class Scheduler Project/backend.0')

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "class_scheduler.settings")
django.setup()

# Load environment variables
env = environ.Env()
env_path = os.path.join("C:/Users/brenn/VSCode Projects/Class Scheduler Project/backend.0", ".env")
environ.Env.read_env(env_path)

from scheduler.models import GradeDistribution

def validate_row(row: List[str]) -> Dict[str, Any]:
    """Validate and convert row data to appropriate types."""
    try:
        # Generate full_course by combining subject and course
        subject = row[2]
        course = row[3]
        full_course = f"{subject}-{course}"

        return {
            'academic_year': row[0],
            'term': row[1],
            'subject': subject,
            'course': course,
            'title': row[4],
            'full_course': full_course,  # Combined field
            'professor': row[5],
            'gpa': float(row[6]) if row[6] else None,
            'a': float(row[7]) if row[7] else None,
            'a_minus': float(row[8]) if row[8] else None,
            'b_plus': float(row[9]) if row[9] else None,
            'b': float(row[10]) if row[10] else None,
            'b_minus': float(row[11]) if row[11] else None,
            'c_plus': float(row[12]) if row[12] else None,
            'c': float(row[13]) if row[13] else None,
            'c_minus': float(row[14]) if row[14] else None,
            'd_plus': float(row[15]) if row[15] else None,
            'd': float(row[16]) if row[16] else None,
            'd_minus': float(row[17]) if row[17] else None,
            'f': float(row[18]) if row[18] else None,
            'withdraws': float(row[19]) if row[19] else None,
            'graded_enrollment': float(row[20]) if row[20] else None,
            'crn': row[21],
            'credit_hours': float(row[22]) if row[22] else None,
        }
    except (IndexError, ValueError) as e:
        raise ValueError(f"Error processing row data: {e}")

def import_grade_distributions(file_path: str, batch_size: int = 1000) -> tuple[int, int]:
    """
    Import grade distributions from CSV file using Django's bulk_create.
    
    Args:
        file_path: Path to the CSV file
        batch_size: Number of records to process in each batch
        
    Returns:
        tuple of (successful_imports, failed_imports)
    """
    successful_imports = 0
    failed_imports = 0
    current_batch = []

    try:
        with open(file_path) as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header row

            for row_number, row in enumerate(reader, start=2):  # Start at 2 to account for header
                try:
                    # Validate and convert row data
                    validated_data = validate_row(row)
                    
                    # Create model instance without saving
                    distribution = GradeDistribution(**validated_data)
                    current_batch.append(distribution)

                    # Process batch if we've reached batch_size
                    if len(current_batch) >= batch_size:
                        with transaction.atomic():
                            GradeDistribution.objects.bulk_create(
                                current_batch,
                                ignore_conflicts=True  # Skip duplicates
                            )
                        successful_imports += len(current_batch)
                        current_batch = []

                except Exception as e:
                    failed_imports += 1
                    print(f"Error processing row {row_number}: {e}")
                    continue

            # Process any remaining records
            if current_batch:
                try:
                    with transaction.atomic():
                        GradeDistribution.objects.bulk_create(
                            current_batch,
                            ignore_conflicts=True
                        )
                    successful_imports += len(current_batch)
                except Exception as e:
                    failed_imports += len(current_batch)
                    print(f"Error processing final batch: {e}")

    except FileNotFoundError:
        print(f"Could not find file: {file_path}")
        return 0, 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return successful_imports, failed_imports

    return successful_imports, failed_imports

def main():
    file_path = "C:/Users/brenn/VSCode Projects/Class Scheduler Project/backend.0/data/grade_distributions.csv"
    successful, failed = import_grade_distributions(file_path)
    
    print(f"\nImport Summary:")
    print(f"Successfully imported: {successful} records")
    print(f"Failed to import: {failed} records")
    print(f"Total processed: {successful + failed} records")

if __name__ == "__main__":
    main()