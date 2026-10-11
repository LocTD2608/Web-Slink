import os
import csv
import sys
from jose import jwt

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.backend.infrastructure.webserver.config import config

def generate_tokens(count: int = 3000, output_file: str = "tests/load_testing/tokens.csv"):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"Generating {count} pre-warmed JWT tokens into {output_file}...")
    
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "student_code", "token"])
        
        for i in range(1, count + 1):
            student_id = f"std-{i:04d}"
            student_code = f"SV2024{i:04d}"
            
            claims = {
                "sub": student_id,
                "student_id": student_id,
                "student_code": student_code,
                "role": "student"
            }
            
            token = jwt.encode(claims, config.jwt_secret, algorithm=config.jwt_algorithm)
            writer.writerow([student_id, student_code, token])
            
    print(f"Successfully generated {count} pre-warmed JWT tokens!")

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    generate_tokens(count=count)
