# ⚠️ CRITICAL: Questions Data Corruption Issue

## Problem Identified

The `data/questions.json` file contains **corrupted answer indices**. All 235 questions have `correct_answer: 0`, which means:

- ✅ Questions where the first option IS the correct answer will work fine
- ❌ Questions where the correct answer is options 1, 2, or 3 will be **graded incorrectly**

## Example of Corruption

```json
{
  "question": "Who was the founder of the Maurya Empire?",
  "options": [
    "Ashoka",
    "Bindusara",
    "Chandragupta Maurya",  // ← This is the CORRECT answer (index 2)
    "Chanakya"
  ],
  "correct_answer": 0  // ← WRONG! Points to "Ashoka" instead
}
```

## Data Analysis

- **Total questions:** 235
- **Correct answer index 0:** 235 (100%)
- **Correct answer index 1:** 0
- **Correct answer index 2:** 0
- **Correct answer index 3:** 0

## Root Cause

This corruption exists in ALL historical git commits (verified back to commit 23a307a), suggesting:
1. The original data source was corrupted
2. Questions were added with a script that defaulted to `correct_answer: 0`
3. The issue went unnoticed because only some questions have option 0 as correct

## How to Fix

### Option 1: Manual Correction (Recommended for Small Sets)

Edit `data/questions.json` and set the correct `correct_answer` index (0-3) for each question:

```json
{
  "question": "Who was the founder of the Maurya Empire?",
  "options": ["Ashoka", "Bindusara", "Chandragupta Maurya", "Chanakya"],
  "correct_answer": 2  // ← Fix the index
}
```

### Option 2: Automated Fix with AI

Use an AI assistant to review all 235 questions and set correct indices:

```bash
# Example using Python and an AI API
python scripts/fix_question_answers.py
```

### Option 3: Replace with Verified Data

If you have a backup or verified question bank, replace the file:

```bash
cp backup/questions.json data/questions.json
```

## Verification Script

After fixing, verify the correction distribution:

```bash
python -c "
import json
data = json.load(open('data/questions.json'))
print(f'Total questions: {len(data)}')
print(f'Correct answer 0: {sum(1 for q in data if q.get(\"correct_answer\") == 0)}')
print(f'Correct answer 1: {sum(1 for q in data if q.get(\"correct_answer\") == 1)}')
print(f'Correct answer 2: {sum(1 for q in data if q.get(\"correct_answer\") == 2)}')
print(f'Correct answer 3: {sum(1 for q in data if q.get(\"correct_answer\") == 3)}')
"
```

A healthy distribution should show answers spread across indices 0-3, not all at 0.

## Impact

**Until this is fixed:**
- Quiz scoring will be incorrect for most questions
- User statistics and leaderboards will be unreliable
- The bot will appear to malfunction

**This is a DATA issue, not a code issue.** The bot's architecture and code are production-ready and functioning correctly.

## Status

📋 **Action Required:** The question bank needs manual review and correction before production deployment.

🔧 **Code Status:** ✅ Production-ready (all refactoring complete)

📊 **Data Status:** ❌ Needs correction
