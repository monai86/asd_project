#!/usr/bin/env python3
"""
Simulate ASR Word Error Rate (WER) and feature drift for Thai child speech readiness planning.
Generates synthetic mock data for 40 Thai-speaking child profiles (TD, ASD, DD) and computes
MLU, TTR, and Echolalia drift metrics under 10%, 25%, and 40% WER configurations.
Saves the results directly to the presentation dashboard's data directory.
"""

import json
import random
from pathlib import Path

# Seed random numbers for reproducibility
random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "presentation-dashboard" / "src" / "data" / "thai_validation_drift.json"

def generate_mock_cases(n_cases=40):
    cases = []
    
    # Ratios: 50% TD (20), 30% ASD (12), 20% DD (8)
    cohort_groups = ["TD"] * 20 + ["ASD"] * 12 + ["DD"] * 8
    
    for i, group in enumerate(cohort_groups):
        case_id = f"TH-{i+1:03d}"
        age_months = random.randint(24, 72)
        
        # Define baseline profiles based on group characteristics
        if group == "TD":
            # TD: High language productivity, high vocabulary diversity, low repetitions
            gold_mlu = round(random.uniform(2.5, 4.8), 2)
            gold_ttr = round(random.uniform(0.48, 0.68), 2)
            gold_echolalia = round(random.uniform(0.0, 0.05), 3)
        elif group == "ASD":
            # ASD: Varied language productivity, lower vocabulary diversity, elevated echolalia
            gold_mlu = round(random.uniform(1.2, 3.2), 2)
            gold_ttr = round(random.uniform(0.35, 0.52), 2)
            gold_echolalia = round(random.uniform(0.12, 0.48), 3)
        else:  # DD (Developmental Delay)
            # DD: Low language productivity, low vocabulary diversity, low/medium repetitions
            gold_mlu = round(random.uniform(1.0, 2.2), 2)
            gold_ttr = round(random.uniform(0.30, 0.46), 2)
            gold_echolalia = round(random.uniform(0.02, 0.15), 3)
            
        cases.append({
            "case_id": case_id,
            "group": group,
            "age_months": age_months,
            "gold_mlu": gold_mlu,
            "gold_ttr": gold_ttr,
            "gold_echolalia": gold_echolalia
        })
        
    return cases

def calculate_drift(cases):
    scatter_data = []
    
    # Lists to accumulate deviations for summary statistics
    deviations = {
        10: {"mlu": [], "ttr": [], "echo": []},
        25: {"mlu": [], "ttr": [], "echo": []},
        40: {"mlu": [], "ttr": [], "echo": []}
    }
    
    for case in cases:
        case_id = case["case_id"]
        group = case["group"]
        age = case["age_months"]
        g_mlu = case["gold_mlu"]
        g_ttr = case["gold_ttr"]
        g_echo = case["gold_echolalia"]
        
        # 10% WER - Minimal Noise (Quiet clinic environment)
        # MLU slightly decreases due to occasional drop of particles (ครับ/ค่ะ)
        # TTR slightly increases due to minor spelling errors (artificial vocabulary expansion)
        # Echolalia slightly decreases
        mlu_10 = max(0.5, round(g_mlu - random.normalvariate(0.06, 0.02), 2))
        ttr_10 = min(1.0, round(g_ttr + random.normalvariate(0.012, 0.005), 2))
        echo_10 = max(0.0, round(g_echo * (1.0 - random.uniform(0.05, 0.15)), 3))
        
        deviations[10]["mlu"].append(mlu_10 - g_mlu)
        deviations[10]["ttr"].append(ttr_10 - g_ttr)
        deviations[10]["echo"].append(echo_10 - g_echo)
        
        # 25% WER - Moderate Noise (Classroom setting, tablet mic)
        # MLU decreases significantly due to particle/connector drops
        # TTR increases due to spelling variations inflating word types
        mlu_25 = max(0.5, round(g_mlu - random.normalvariate(0.24, 0.05), 2))
        ttr_25 = min(1.0, round(g_ttr + random.normalvariate(0.045, 0.015), 2))
        echo_25 = max(0.0, round(g_echo * (1.0 - random.uniform(0.20, 0.40)), 3))
        
        deviations[25]["mlu"].append(mlu_25 - g_mlu)
        deviations[25]["ttr"].append(ttr_25 - g_ttr)
        deviations[25]["echo"].append(echo_25 - g_echo)
        
        # 40% WER - Severe Noise (Background chatter, distant mic)
        # MLU drops dramatically (e.g. half of the words missed)
        # TTR inflates heavily with gibberish spellings
        mlu_40 = max(0.5, round(g_mlu - random.normalvariate(0.48, 0.10), 2))
        ttr_40 = min(1.0, round(g_ttr + random.normalvariate(0.095, 0.030), 2))
        echo_40 = max(0.0, round(g_echo * (1.0 - random.uniform(0.45, 0.70)), 3))
        
        deviations[40]["mlu"].append(mlu_40 - g_mlu)
        deviations[40]["ttr"].append(ttr_40 - g_ttr)
        deviations[40]["echo"].append(echo_40 - g_echo)
        
        scatter_data.append({
            "case_id": case_id,
            "group": group,
            "age_months": age,
            "gold_mlu": g_mlu,
            "gold_ttr": g_ttr,
            "gold_echolalia": g_echo,
            "wer_10": {"asr_mlu": mlu_10, "asr_ttr": ttr_10, "asr_echolalia": echo_10},
            "wer_25": {"asr_mlu": mlu_25, "asr_ttr": ttr_25, "asr_echolalia": echo_25},
            "wer_40": {"asr_mlu": mlu_40, "asr_ttr": ttr_40, "asr_echolalia": echo_40}
        })
        
    # Calculate aggregate summary stats for each WER tier
    drift_summary = []
    wer_configs = [
        {"wer": 10, "label_en": "10% WER (Quiet Clinic Room)", "label_th": "10% WER (ห้องคลินิกเงียบ)"},
        {"wer": 25, "label_en": "25% WER (Classroom Tablet Mic)", "label_th": "25% WER (ไมโครโฟนแท็บเล็ตในห้องเรียน)"},
        {"wer": 40, "label_en": "40% WER (Background Play Noise)", "label_th": "40% WER (สภาพแวดล้อมสนามเด็กเล่นมีเสียงรบกวน)"}
    ]
    
    for cfg in wer_configs:
        wer = cfg["wer"]
        mlu_devs = deviations[wer]["mlu"]
        ttr_devs = deviations[wer]["ttr"]
        echo_devs = deviations[wer]["echo"]
        
        mlu_mae = round(sum(abs(d) for d in mlu_devs) / len(mlu_devs), 3)
        mlu_bias = round(sum(mlu_devs) / len(mlu_devs), 3)
        
        ttr_mae = round(sum(abs(d) for d in ttr_devs) / len(ttr_devs), 3)
        ttr_bias = round(sum(ttr_devs) / len(ttr_devs), 3)
        
        echo_mae = round(sum(abs(d) for d in echo_devs) / len(echo_devs), 4)
        echo_bias = round(sum(echo_devs) / len(echo_devs), 4)
        
        drift_summary.append({
            "wer_value": wer,
            "label_en": cfg["label_en"],
            "label_th": cfg["label_th"],
            "mlu_mae": mlu_mae,
            "mlu_bias": mlu_bias,
            "ttr_mae": ttr_mae,
            "ttr_bias": ttr_bias,
            "echolalia_mae": echo_mae,
            "echolalia_bias": echo_bias
        })
        
    return scatter_data, drift_summary

def get_thai_error_distribution():
    # Return categorized ASR error types specific to Thai language modeling
    return [
        {
            "error_type": "Particle Deletion (การตกหล่นของคำลงท้ายและคำช่วย)",
            "frequency": 42,
            "effect": "ส่งผลลบโดยตรงต่อ MLU ทำให้เด็กดูเหมือนพูดประโยคสั้นกว่าความเป็นจริงทางคลินิก (เช่น ครับ/ค่ะ/นะ/ฮะ หายไป)",
            "solution": "เพิ่มระบบตรวจสอบคำลงท้ายแบบ Rule-based หรือใช้ Custom Language Model หลังประมวลผลเสียง"
        },
        {
            "error_type": "Repetition Distortion (การรวมพยางค์ซ้ำเลียนแบบเข้าด้วยกัน)",
            "frequency": 28,
            "effect": "ASR แปลงเสียงกระตุกหรือคำซ้ำผิดพลาด (เช่น 'หม่ำ-หม่ำ-หม่ำ' ถูกรวบเหลือ 'หม่ำ') ทำให้ตรวจจับ Echolalia หรืออาการจดจ่อคำซ้ำคลาดเคลื่อน",
            "solution": "ปิดฟังก์ชัน Speech Aggregation หรือปรับ VAD threshold ให้สั้นลงเพื่อจับจังหวะกระตุกเสียงพยางค์ซ้ำ"
        },
        {
            "error_type": "Morphological Boundary Error (ความผิดพลาดในการแบ่งแยกคำภาษาไทย)",
            "frequency": 35,
            "effect": "คำเชื่อมประโยคถูกแบ่งผิดทางสัณฐานวิทยา ส่งผลต่อ TTR และจำนวนคำทั้งหมดในชุดข้อมูล",
            "solution": "เปลี่ยนไปใช้ตัวตัดคำ (Word Segmenter) ที่ฝึกด้วยข้อมูลเสียงพูดธรรมชาติแทนการตัดคำจากเอกสารทางราชการ"
        },
        {
            "error_type": "Tonal/Vowel Shift Spellings (การถอดอักขระเสียงเพี้ยน ทำให้เกิดคำสะกดรูปแบบใหม่)",
            "frequency": 19,
            "effect": "ทำให้คำเดิมถูกแกะเสียงเพี้ยนไปคนละสะกด (เช่น 'กินข้าว' เป็น 'กิ๊นข๊าว') ส่งผลให้ค่าสถิติ TTR สูงกว่าจริงเกินควร (Vocabulary Inflation)",
            "solution": "ทำ Spell-checking map หรือปรับพจนานุกรมคำศัพท์ (Phoneme-to-Grapheme Map) ให้มีความยืดหยุ่นต่อสำเนียงของเด็ก"
        }
    ]

def main():
    print("[Simulate Thai Drift] Generating mock dataset...")
    cases = generate_mock_cases()
    scatter_data, drift_summary = calculate_drift(cases)
    error_dist = get_thai_error_distribution()
    
    payload = {
        "metadata": {
            "description": "Synthetic Thai ASR Drift Simulation Data",
            "n_cases": len(cases),
            "data_type": "synthetic_mock_simulation",
            "clinical_validation_status": "not_validated_for_thai_children",
            "generated_at": "2026-06-03"
        },
        "scatter_data": scatter_data,
        "drift_summary": drift_summary,
        "error_distribution": error_dist
    }
    
    # Ensure directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    print(f"[Simulate Thai Drift] Successfully wrote JSON data to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
