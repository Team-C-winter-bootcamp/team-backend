import os
import django
import json
import re
import glob

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from precedents.models import Precedent, ReferenceRule, RelationRule

def parse_reference_rules(text):
    rules = []
    
    # Split by comma that is not inside parentheses
    parts = re.split(r',\s*(?![^()]*\))', text)
    
    for part in parts:
        # Then split by slash
        slash_split = part.split('/')
        
        for sub_part in slash_split:
            sub_part = sub_part.strip()
            
            law_type = None
            article_no = None

            # First, clean the sub_part from any content in parentheses or leading [숫자]
            cleaned_sub_part = re.sub(r'\(.*\)', '', sub_part).strip()
            cleaned_sub_part = re.sub(r'^\[\d+\]\s*', '', cleaned_sub_part).strip() # Remove leading [숫자]

            # Focus solely on "Law Name 제XX조" pattern
            law_match = re.search(r'(.+?(?:법|칙|령|률))\s*제(\d+)조', cleaned_sub_part)
            
            if law_match:
                potential_law_type = law_match.group(1).strip()
                potential_article_no = int(law_match.group(2))

                # Further validate potential_law_type to ensure it doesn't contain "제X항", "제X조", "제X호", "별표"
                if not re.search(r'제\d+(?:조|항|호)', potential_law_type) and \
                   not potential_law_type.startswith('별표') and \
                   not potential_law_type.endswith('호'): # Check for ending with "호"
                    law_type = potential_law_type
                    article_no = potential_article_no

            if law_type and article_no:
                # Final cleaning for law_type
                law_type = re.sub(r'^\d+\s*', '', law_type).strip() # Remove leading numbers like "1 민법"
                law_type = re.sub(r'^\s*제\d+항\s*', '', law_type).strip() # Remove leading 제X항
                law_type = re.sub(r'\[.*\]', '', law_type).strip()  # Remove any remaining [.*]
                law_type = law_type.strip("[]") # Remove leading/trailing brackets
                law_type = re.sub(r'^【참조문헌】\s*', '', law_type).strip() # Remove 【참조문헌】
                law_type = re.sub(r'^부칙\s*', '', law_type).strip() # Remove 부칙
                law_type = re.sub(r'^(?:[a-zA-Z]\s*항|[가-힣]\.)\s*', '', law_type).strip() # Remove c항, 가. etc.
                law_type = re.sub(r'^(?:[가-힣]\.\s*)+', '', law_type).strip() # Remove 나.다. etc.
                law_type = re.sub(r'^같은\s*법\s*', '', law_type).strip() # Remove 같은법
                law_type = re.sub(r'^]\s*', '', law_type).strip()  # Remove leading ']'
                law_type = re.sub(r'^\s*\]', '', law_type).strip()  # Remove leading ']'
                law_type = law_type.strip("[]")  # Remove leading/trailing brackets

                # Exclude generic law types
                generic_law_types = ["동법", "률", "시행령", "동 시행령", "법", "칙", "령"]
                if law_type in generic_law_types:
                    law_type = None # Invalidate this law type

                # One last check to ensure no "호" or "별표" patterns remain in law_type after all cleaning
                if law_type and not law_type.endswith('호') and not law_type.startswith('별표'):
                    rules.append((law_type, article_no))

    return rules

def main():
    # Clear existing relation rules and reset PK sequence
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE precedents_relationrule RESTART IDENTITY CASCADE;")
    print("Cleared all existing relation rules and reset primary key sequence.")

    file_paths = glob.glob('1.데이터/Training/02.라벨링데이터/**/*.json', recursive=True)
    file_paths.extend(glob.glob('1.데이터/Validation/02.라벨링데이터/**/*.json', recursive=True))

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Get Precedent
                info = data.get("info", {})
                case_no_raw = info.get("caseNo")
                if not case_no_raw:
                    print(f"Warning: No caseNo found in {file_path}")
                    continue
                
                case_no = case_no_raw.split(',')[0].strip()
                
                try:
                    precedent = Precedent.objects.get(case_no=case_no)
                except Precedent.DoesNotExist:
                    print(f"Warning: Precedent with case_no '{case_no}' not found. Skipping {file_path}")
                    continue
                    
                # Get Reference Rules and create relations
                reference_info = data.get("Reference_info")
                if reference_info:
                    reference_rules_str = reference_info.get("reference_rules")
                    if reference_rules_str:
                        parsed_rules = parse_reference_rules(reference_rules_str)
                        
                        for law_type, article_no in parsed_rules:
                            try:
                                reference_rule = ReferenceRule.objects.get(law_type=law_type, article_no=article_no)
                                
                                # Create the relation
                                obj, created = RelationRule.objects.get_or_create(
                                    precedent=precedent,
                                    reference_rule=reference_rule
                                )
                                if created:
                                    print(f"Created relation: {case_no} -> {law_type} 제{article_no}조")

                            except ReferenceRule.DoesNotExist:
                                print(f"Warning: ReferenceRule '{law_type} 제{article_no}조' not found. Cannot create relation for {case_no}")

        except json.JSONDecodeError:
            print(f"Error decoding JSON from file: {file_path}")
        except Exception as e:
            print(f"An error occurred with file {file_path}: {e}")

    print("Data insertion for relation rules complete.")

if __name__ == "__main__":
    main()