# References

> **หมายเหตุ:** แหล่งอ้างอิงทั้งหมดเกี่ยวกับโปรเจกต์ AI-Assisted Clinical Assessment of Autism  
> **รูปแบบ:** APA style (modified for clarity)  
> **วันที่:** 23 เมษายน 2026

---

## 1. Clinical Linguistics & Speech-Language Features

**Brown, R. (1973).** *A first language: The early stages.* Harvard University Press.  
> **ใช้เพราะ:** MLU (Mean Length of Utterance) เป็น gold standard ประเมินการพัฒนาภาษาเด็กมา 50+ ปี ใช้แบ่ง Brown's stages I–V ซึ่งเราใช้ใน feature extraction

**Templin, M. (1957).** *Certain language skills in children.* University of Minnesota Press.  
> **ใช้เพราะ:** TTR (Type-Token Ratio) เป็นดัชนีความหลากหลายของคำที่ใช้ประเมิน vocabulary และ echolalia

**Miller, J. (1984).** *Assessing language production in children.* University Park Press.  
> **ใช้เพราะ:** งานวิจัยพื้นฐานเกี่ยวกับ MLU, TTR และ productivity measures ในเด็ก

**Shriberg, L. D., & Kwiatkowski, J. (1994).** *Speech and language impairment in children: Causes, characteristics, intervention, and outcome.* Singular Publishing Group.  
> **ใช้เพราะ:** เกี่ยวกับ unintelligible speech และ phonological disorders ที่เราใช้ feature `unintelligible_ratio` ประเมิน

**Paul, R., et al. (2017).** *Speech and language disorders in children.* Oxford University Press.  
> **ใช้เพราะ:** Social communication deficits ใน ASD รวมถึง question ratio, pragmatic markers

---

## 2. Autism Spectrum Disorder (ASD) Clinical Criteria

**American Psychiatric Association. (2013).** *Diagnostic and statistical manual of mental disorders* (5th ed.). American Psychiatric Publishing.  
> **ใช้เพราะ:** DSM-5 criteria สำหรับ ASD — ใช้เชื่อม features ของเรากับ core symptoms (social communication deficit, restricted/repetitive behaviors)

**Lord, C., Risi, S., Lambrecht, L., Cook, E. H., Leventhal, B. L., DiLavore, P. C., ... & Risi, S. (2000).** The Autism Diagnostic Observation Schedule–Generic: A standard measure of social and communication deficits associated with the spectrum of autism. *Journal of Autism and Developmental Disorders, 30*(3), 205-223.  
> **ใช้เพราะ:** ADOS เป็น gold standard สำหรับ ASD diagnosis — เราใช้เปรียบเทียบกับ model ของเรา

**Tager-Flusberg, H., et al. (2005).** *Language development in children with autism spectrum disorders.* In P. Fletcher & J. MacWhinney (Eds.), *The handbook of language acquisition* (pp. 479-497). Blackwell.  
> **ใช้เพราะ:** Review ของ language profiles ใน ASD รวมถึง MLU, TTR, unintelligible speech ที่เราใช้

**Mundy, P., et al. (2007).** *Joint attention and autism.* In D. Cohen (Ed.), *Handbook of autism and pervasive developmental disorders* (3rd ed., pp. 650-681). Wiley.  
> **ใช้เพราะ:** Joint attention เป็น core deficit ใน ASD — เราอยากเพิ่ม feature นี้ในอนาคต

---

## 3. CHAT Format & TalkBank / ASDBank

**MacWhinney, B. (2000).** *The CHILDES project: Tools for analyzing talk* (3rd ed.). Lawrence Erlbaum Associates.  
> **ใช้เพราะ:** CHAT format คือมาตรฐาน transcript ที่ TalkBank/ASDBank ใช้ — เราใช้ pylangacq อ่าน .cha files ตามมาตรฐานนี้

**MacWhinney, B. (2000).** *The CHAT manual.* Carnegie Mellon University.  
> **ใช้เพราะ:** คู่มืออธิบาย CHAT format ให้ละเอียด — เราใช้สร้าง .cha จาก audio pipeline

**TalkBank. (n.d.).** *ASDBank: Autism Spectrum Disorder Database.* Retrieved from https://asd.talkbank.org/  
> **ใช้เพราะ:** Dataset หลักที่เราดาวน์โหลด .cha files มา (Eigsti, Nadig, NYU-Emerson, Flusberg, Rollins)

**Sagae, K., et al. (ongoing).** *pylangacq: A Python library for CHAT transcripts.* Retrieved from https://github.com/pylangacq/pylangacq  
> **ใช้เพราะ:** Library ที่เราใช้อ่าน .cha files และ extract features

---

## 4. Dataset-Specific References

**Eigsti, I.-M., et al. (Year).** *Eigsti corpus.* TalkBank / ASDBank.  
> **ใช้เพราะ:** Corpus หนึ่งใน 5 corpora ที่เราใช้ (ASD 16, DD 16, TD 16)

**Nadig, A., et al. (Year).** *Nadig corpus.* TalkBank / ASDBank.  
> **ใช้เพราะ:** Corpus ที่เป็น case-control design (ASD 13, TD 25)

**Emerson, K., et al. (Year).** *NYU-Emerson corpus.* TalkBank / ASDBank.  
> **ใช้เพราะ:** Corpus ที่มี video/audio ด้วย (ASD 30)

**Tager-Flusberg, H., & Anderson, M. (Year).** *Flusberg corpus.* TalkBank / ASDBank.  
> **ใช้เพราะ:** Longitudinal corpus ที่ใช้ใน progress tracking (6 เด็ก, 64 sessions)

**Rollins, P. (Year).** *Rollins corpus.* TalkBank / ASDBank.  
> **ใช้เพราะ:** Longitudinal corpus หลักสำหรับ progress tracking (5 เด็ก, 21 sessions)

> **หมายเหตุ:** Corpora หลายตัวไม่มี journal publication แยก — อ้างอิงผ่าน TalkBank/ASDBank โดยตรง

---

## 5. Machine Learning Methods

**Kohavi, R. (1995).** A study of cross-validation and bootstrap for accuracy estimation and model selection. *Proceedings of the 14th International Joint Conference on Artificial Intelligence* (IJCAI), 1137-1143.  
> **ใช้เพราะ:** เราใช้ Stratified 5-fold Cross-Validation เพื่อประเมิน model performance

**Hanley, J. A., & McNeil, B. J. (1982).** The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology, 143*(1), 29-36.  
> **ใช้เพราะ:** เราใช้ ROC-AUC เป็น metric หลักสำหรับ binary classification

**Pedregosa, F., et al. (2011).** Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830.  
> **ใช้เพราะ:** Library ที่เราใช้ train Logistic Regression, SVM, Random Forest

**Breiman, L. (2001).** Random forests. *Machine Learning, 45*(1), 5-32.  
> **ใช้เพราะ:** Random Forest model ที่เราใช้ใน multi-class classification

**James, G., Witten, D., Hastie, T., & Tibshirani, R. (2013).** *An introduction to statistical learning: With applications in R.* Springer.  
> **ใช้เพราะ:** อ้างอิง general ML concepts (LogReg, SVM, RF, CV) สำหรับ term paper

**Goodfellow, I., Bengio, Y., & Courville, A. (2016).** *Deep learning.* MIT Press.  
> **ใช้เพราะ:** MLP และ Bi-LSTM ที่เรา implement ใน deep_learning.py

**Hochreiter, S., & Schmidhuber, J. (1997).** Long short-term memory. *Neural Computation, 9*(8), 1735-1780.  
> **ใช้เพราะ:** Bi-LSTM architecture ที่เราใช้ใน deep learning module

---

## 6. Speech Recognition & Audio Processing

**Radford, A., et al. (2022).** Robust speech recognition via large-scale weak supervision. *International Conference on Machine Learning (ICML).*  
> **ใช้เพราะ:** Whisper ASR model ที่เราใช้ใน audio pipeline

**Guzhov, A., et al. (2022).** *faster-whisper: Faster Whisper implementation with CTranslate2.* Retrieved from https://github.com/guillaumekln/faster-whisper  
> **ใช้เพราะ:** faster-whisper wrapper ที่เราใช้แทน OpenAI Whisper (4x faster)

**Bredin, H., et al. (2021/2023).** *pyannote.audio: Neural building blocks for speaker diarization.* Interspeech / arXiv.  
> **ใช้เพราะ:** pyannote speaker diarization model ที่เราใช้เป็น optional backend

**McFee, B., et al. (2015).** librosa: Audio and music signal analysis in Python. *Proceedings of the 14th Python in Science Conference (SCIPY).*  
> **ใช้เพราะ:** Library ที่เราใช้ใน PitchHeuristicDiarizer (F0 estimation สำหรับแยกเด็ก/ผู้ใหญ่)

---

## 7. Data Analysis & Visualization

**McKinney, W. (2010).** Data structures for statistical computing in Python. *Proceedings of the 9th Python in Science Conference (SCIPY), 445, 51-56.*  
> **ใช้เพรถะ:** pandas library ที่เราใช้จัดการ DataFrames ทั้งหมด

**Hunter, J. D. (2007).** Matplotlib: A 2D graphics environment. *Computing in Science & Engineering, 9*(3), 90-95.  
> **ใช้เพรถะ:** matplotlib ที่เราใช้สร้าง plots ใน eda.py

**Waskom, M. (2021).** seaborn: statistical data visualization. *Journal of Open Source Software, 6*(60), 3021.  
> **ใช้เพรถะ:** seaborn ที่เราใช้สร้าง visualizations ใน dashboard

---

## 8. Deployment & Web Framework

**Streamlit. (n.d.).** *Streamlit: Turn data scripts into shareable web apps.* Retrieved from https://streamlit.io/  
> **ใช้เพรถะ:** Framework ที่เราใช้สร้าง interactive dashboard (app/dashboard.py)

**Docker. (n.d.).** *Docker: Container platform.* Retrieved from https://www.docker.com/  
> **ใช้เพรถะ:** Containerization สำหรับ deployment (Dockerfile)

---

## 9. Evaluation Metrics

**Sokolova, M., & Lapalme, G. (2009).** A systematic analysis of performance measures for classification tasks. *Information Processing & Management, 45*(4), 427-437.  
> **ใช้เพรถะ:** เราใช้ Accuracy, F1-macro, ROC-AUC — paper นี้อธิบาย trade-offs ระหว่าง metrics

---

## 10. AI for ASD Diagnosis (Recent Literature, 2019–2025)

> **หมายเหตุ:** Papers เหล่านี้รวบรวมจาก Consensus.app — ดู metadata เต็มที่ [`literature/consensus_papers_2026-04-26.csv`](./literature/consensus_papers_2026-04-26.csv)

### 10.1 Speech & Language-based AI (ใกล้กับ project มากที่สุด)

**Themistocleous, C., Andreou, M., & Peristeri, E. (2024).** Autism Detection in Children: Integrating Machine Learning and Natural Language Processing in Narrative Analysis. *Frontiers in Psychology.*
> **ใช้เพราะ:** ML + NLP จาก narrative/vocabulary skills ได้ accuracy 96% — ตรงกับวิธีของเรา (CHAT features + LogReg)

**Eni, M., Zigel, Y., Ilan, M., et al. (2025).** Reliably quantifying the severity of social symptoms in children with autism using ASDSpeech. *Scientific Reports.*
> **ใช้เพราะ:** ASDSpeech algorithm เทรนด้วย 99,193 vocalizations จาก ADOS-2 — สนับสนุน rationale ของการใช้ speech features quantify ASD severity

**Mohammadi, F., Shahrokhi, H., Asadzadeh, A., et al. (2025).** Artificial Intelligence in Autism Spectrum Disorder Diagnosis: A Scoping Review of Face, Voice, and Text Analysis Methods.
> **ใช้เพราะ:** Scoping review ครอบคลุม voice + text analysis (accuracy 70–98%) — สนับสนุน feature selection ของเรา

**Rakotomanana, H., & Rouhafzay, G. (2025).** A Scoping Review of AI-Based Approaches for Detecting Autism Traits Using Voice and Behavioral Data. *Bioengineering, 12*(11), 1136.
> **ใช้เพราะ:** Scoping review 158 studies (2015–2025) — ใช้อ้าง challenges (dataset heterogeneity, gender bias, small samples)

### 10.2 Multi-modal AI Diagnosis

**Abbas, H., Garberson, F., Liu-Mayo, S., Glover, E., & Wall, D. (2020).** Multi-modular AI Approach to Streamline Autism Diagnosis in Young Children. *Scientific Reports.* DOI: 10.1038/s41598-020-61213-w
> **ใช้เพราะ:** Multi-modular AI (questionnaire + video + clinician) — แนวทาง future work ของเราในการรวม modalities

**Megerian, J. T., Dey, S., Melmed, R., et al. (2022).** Evaluation of an artificial intelligence-based medical device for diagnosis of autism spectrum disorder.
> **ใช้เพราะ:** FDA-cleared AI device (PPV 80.8%, NPV 98.3%) — proof-of-concept ว่า AI deployable ใน clinical setting

### 10.3 ML/DL for ASD Screening

**Vakadkar, K., Purkayastha, D., & Krishnan, D. (2021).** Detection of Autism Spectrum Disorder in Children Using Machine Learning Techniques. *SN Computer Science.* DOI: 10.1007/s42979-021-00776-5
> **ใช้เพราะ:** เปรียบเทียบ SVM, RFC, NB, **LogReg, KNN** — Logistic Regression ได้ accuracy ดีที่สุด ตรงกับ choice ของเรา

**Shahamiri, S. R., & Thabtah, F. (2020).** Autism AI: a New Autism Screening System Based on Artificial Intelligence.
> **ใช้เพราะ:** CNN-based screening — สนับสนุนการใช้ deep learning (ของเรามี Bi-LSTM)

**Rubio-Martín, S., García-Ordás, M. T., Bayón-Gutiérrez, M., et al. (2024).** Enhancing ASD detection accuracy: a combined approach of machine learning and deep learning models with natural language processing.
> **ใช้เพราะ:** ML + DL + NLP (RNN, LSTM, **Bi-LSTM**, BERT) บน Twitter — สนับสนุน Bi-LSTM choice ของเรา

**Jeon, I., Kim, M., So, D., et al. (2024).** Reliable Autism Spectrum Disorder Diagnosis for Pediatrics Using Machine Learning and Explainable AI.
> **ใช้เพราะ:** XAI + ML — แนวทาง future work เพื่อเพิ่ม interpretability ของ model เรา

### 10.4 Reviews & Meta-analyses

**Sun, C., McEwan, A., Boulton, K. A., et al. (2025).** Artificial intelligence for tracking social behaviours and supporting an autism spectrum disorder diagnosis: systematic review and meta-analysis. *eBioMedicine.* DOI: 10.1016/j.ebiom.2025.105931
> **ใช้เพราะ:** Meta-analysis ใน Q1 journal — หลักฐานว่า AI augment ASD assessment ได้

**Joudar, S. S., Albahri, A., Hamid, R. A., et al. (2023).** Artificial intelligence-based approaches for improving the diagnosis, triage, and prioritization of autism spectrum disorder: a systematic review.
> **ใช้เพราะ:** Systematic review of 46 papers — กรอบการเปรียบเทียบ project ของเรากับ state-of-the-art

**Song, D. Y., Kim, S. Y., Bong, G., Kim, J. M., & Yoo, H. (2019).** The Use of Artificial Intelligence in Screening and Diagnosis of Autism Spectrum Disorder: A Literature Review. *Journal of the Korean Academy of Child and Adolescent Psychiatry.*
> **ใช้เพราะ:** อธิบาย real-world challenges ของ AI ใน ASD healthcare — สนับสนุน limitation section

**Solek, P., Nurfitri, E., Sahril, I., et al. (2025).** The Role of Artificial Intelligence for Early Diagnostic Tools of Autism Spectrum Disorder: A Systematic Review.
> **ใช้เพราะ:** PRISMA 2020 systematic review (25 studies, age 0–18) — สนับสนุน early diagnosis rationale

**Zhang, S. (2025).** AI-assisted early screening, diagnosis, and intervention for autism in young children.
> **ใช้เพราะ:** Review ครอบคลุม screening + diagnosis + intervention — กรอบ scope ของ field

**Wankhede, N., Kale, M. B., Shukla, M., et al. (2024).** Leveraging AI for the diagnosis and treatment of autism spectrum disorder. *Asian Journal of Psychiatry.*
> **ใช้เพราะ:** Q1 review — current trends + future prospects

### 10.5 Other Modalities (Brain Imaging, Motion)

**Helmy, E., Elnakib, A., Elnakieb, Y., et al. (2023).** Role of Artificial Intelligence for Autism Diagnosis Using DTI and fMRI: A Survey.
> **ใช้เพราะ:** AI + brain imaging — เปรียบเทียบ modality ของเรา (speech) กับ neuroimaging

**Simeoli, R., Rega, A., Cerasuolo, M., et al. (2024).** Using Machine Learning for Motion Analysis to Early Detect Autism Spectrum Disorder: A Systematic Review.
> **ใช้เพราะ:** ML + motion — alternative modality, อ้างอิงเปรียบเทียบ

**Sideraki, A., & Anagnostopoulos, C.-N. (2025).** The use of Artificial Intelligence for Intervention and Assessment in Individuals with ASD. *ArXiv.*
> **ใช้เพราะ:** AI สำหรับ intervention (NAO, Kaspar robots) — future work direction

**Rasul, R. A., Saha, P., Bala, D., et al. (2023).** An evaluation of machine learning approaches for early diagnosis of autism spectrum disorder. *Healthcare Analytics.*
> **ใช้เพราะ:** เปรียบเทียบ ML approaches — spectral clustering best, สนับสนุน model selection

---

## 11. Additional Future References (ถ้าจะต่อยอด)

**Prizant, B. M. (1983).** Echolalia in autism: Assessment, intervention, and theoretical considerations. *Journal of Child Psychology and Psychiatry, 24*(3), 399-418.  
> **ใช้เพรถะ:** Reference สำหรับ feature "echolalia ratio" ที่อยากเพิ่มในอนาคต

**Rutter, M. (1978).** Diagnosis and definition of childhood autism. *Journal of Autism and Childhood Schizophrenia, 8*(2), 139-161.  
> **ใช้เพรถะ:** Historical context ของ ASD diagnosis

---

## หมายเหตุ

- **Corpora บน TalkBank:** หลายตัวไม่มี journal publication แยก — อ้างอิงผ่าน `asd.talkbank.org` โดยตรง
- **Software libraries:** บางตัวไม่มี peer-reviewed paper (เช่น faster-whisper, pylangacq) — อ้างอิงผ่าน GitHub repo หรือ documentation
- **Thai assessment scales:** ถ้าจะต่อยอดด้วยข้อมูลไทย ต้องเพิ่ม references สำหรับ REELS, TDMI, ADOS-2 Thai version ฯลฯ
