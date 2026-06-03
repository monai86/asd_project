import React, { useState } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  FileText,
  Layers,
  MessageSquare,
  Play,
  TrendingUp,
  Users,
  ShieldCheck,
  UserCheck,
  Zap,
  Search,
  Filter,
  FileSpreadsheet,
} from "lucide-react";
import projectData from "../data/project_data.json";
import thaiDriftData from "../data/thai_validation_drift.json";


// Colors
const PASTEL_COLORS = {
  blue: "#A0C4FF",
  purple: "#BDB2FF",
  green: "#CAFFBF",
  peach: "#FFD6A5",
  pink: "#FFADAD",
  yellow: "#FDFFB6",
};

const CLINICAL_COLORS = {
  blue: "#1A73E8",
  purple: "#7F56D9",
  green: "#1E8E3E",
  peach: "#D97706",
};

// Dynamic Thai translations for the 14 features
const FEATURE_TRANSLATIONS: Record<string, { title: string; clinical_meaning: string; caveat: string; group: string }> = {
  age_months: {
    title: "อายุเป็นเดือน (Age)",
    clinical_meaning: "ควบคุมความแตกต่างด้านพัฒนาการทางภาษาตามปกติของเด็กแต่ละช่วงวัย",
    caveat: "การกระจายตัวของอายุแตกต่างกันในแต่ละคลังข้อมูล ไม่ควรใช้แปลผลเป็นสัญญาณออทิสติกโดยตรง",
    group: "ประชากรศาสตร์"
  },
  total_utterances: {
    title: "จำนวนประโยค (Utterances)",
    clinical_meaning: "จำนวนประโยคทั้งหมดที่เด็กพูดในเซสชัน สะท้อนถึงระดับการมีส่วนร่วมสื่อสาร",
    caveat: "ความยาวของกิจกรรมบันทึกเสียงและรูปแบบการตอบโต้ของครูหรือผู้ประเมินมีผลต่อจำนวนประโยคอย่างมาก",
    group: "การพูด"
  },
  mlu: {
    title: "ความยาวประโยคเฉลี่ย (MLU)",
    clinical_meaning: "ตัววัดความซับซ้อนทางไวยากรณ์ตามมาตรฐานสากล",
    caveat: "ขึ้นอยู่กับลักษณะโครงสร้างไวยากรณ์ของแต่ละภาษา คุณภาพการถอดเสียง และความถูกต้องของเครื่องมือสแกน",
    group: "ความซับซ้อนโครงสร้าง"
  },
  mluw: {
    title: "ความยาวประโยคเฉลี่ย (MLUw)",
    clinical_meaning: "ความยาวประโยคอย่างง่าย มีประโยชน์มากในกรณีที่การแยกหน่วยคำมีความยากลำบาก",
    caveat: "อาจได้ค่าสูงเกินจริงในกรณีที่เด็กพูดประโยคซ้ำๆ เดิม หรือถูกผู้ประเมินกระตุ้นนำบ่อยๆ",
    group: "ความซับซ้อนโครงสร้าง"
  },
  ttr: {
    title: "ความหลากหลายคำศัพท์ (TTR)",
    clinical_meaning: "ประเมินความหลากหลายและความกว้างขวางของคำศัพท์ที่เด็กใช้ในบทสนทนา",
    caveat: "อ่อนไหวต่อจำนวนคำรวม (หากพูดเยอะ ค่า TTR จะลดลงตามธรรมชาติ) ควรเปรียบเทียบในความยาวใกล้เคียงกัน",
    group: "ความหลากหลายคำศัพท์"
  },
  total_words: {
    title: "จำนวนคำทั้งหมด (Total Words)",
    clinical_meaning: "ตัวบ่งชี้ปริมาณการสื่อสารเพื่อแสดงออกทางภาษาในระหว่างเล่นหรือประเมิน",
    caveat: "ขึ้นอยู่กับเวลาบันทึกเสียงและระดับความเป็นมิตรของสภาพแวดล้อม",
    group: "การพูด"
  },
  unintelligible_count: {
    title: "ประโยคที่ฟังไม่ชัดเจน (Count)",
    clinical_meaning: "นับจำนวนประโยคหรือกลุ่มคำที่ถอดเสียงไม่ได้เนื่องจากพูดไม่ชัดหรือเสียงไม่เคลียร์",
    caveat: "ระบบถอดคำพูดอัตโนมัติ (ASR) อาจตรวจไม่พบคำที่ฟังไม่ชัดหากไม่มีผู้บำบัดช่วยตรวจสอบบทสนทนา",
    group: "พฤติกรรมเฉพาะออทิสติก"
  },
  unintelligible_ratio: {
    title: "สัดส่วนประโยคไม่ชัดเจน (Ratio)",
    clinical_meaning: "สัดส่วนประโยคที่ผู้ประเมินฟังไม่เข้าใจ โดยปรับค่าให้สอดคล้องกับขนาดบทสนทนา",
    caveat: "ควรพิจารณาร่วมกับระดับคุณภาพของเสียงบันทึกและสัญญาณรบกวนในห้อง",
    group: "พฤติกรรมเฉพาะออทิสติก"
  },
  zero_vocalization_count: {
    title: "การไม่พูดโต้ตอบ (Zero Voc.)",
    clinical_meaning: "จังหวะการเว้นว่างหรือการไม่พูดโต้ตอบในบทสนทนาเมื่อถึงคิวของตนเอง",
    caveat: "อาจเกิดจากบริบทการทำกิจกรรมบางประเภทมากกว่าความสามารถทางภาษาที่แท้จริงของเด็ก",
    group: "พฤติกรรมเฉพาะออทิสติก"
  },
  nonverbal_vocalization_count: {
    title: "เสียงที่ไม่ใช่คำพูด (Non-verbal)",
    clinical_meaning: "การส่งเสียงหัวเราะ เสียงกรีดร้อง หรือเสียงพึมพำที่ไม่ใช่คำศัพท์ภาษา",
    caveat: "การส่งเสียงที่ไม่ใช่ภาษาบางประเภทเป็นเรื่องทางบวก เช่น การหัวเราะร่วมกันกับคู่สนทนา",
    group: "พฤติกรรมเฉพาะออทิสติก"
  },
  question_ratio: {
    title: "สัดส่วนประโยคคำถาม (Ratio)",
    clinical_meaning: "ประเมินการสื่อสารเชิงรุกและความสามารถในการสร้างความสัมพันธ์ทางสังคม (Pragmatics)",
    caveat: "ขึ้นอยู่กับการออกแบบกิจกรรมในเซสชันและการเหนี่ยวนำของนักบำบัดรักษา",
    group: "การสื่อสารทางสังคม"
  },
  echolalia_count: {
    title: "การพูดเลียนเสียง (Count)",
    clinical_meaning: "ความถี่ของการทวนคำพูดของคู่สนทนาทันทีโดยไม่มีการปรับเปลี่ยนโครงสร้างประโยค",
    caveat: "การตรวจจับด้วยระบบต้องอาศัยผู้เชี่ยวชาญช่วยยืนยันความหมายตามบริบทประกอบด้วย",
    group: "พฤติกรรมเฉพาะออทิสติก"
  },
  echolalia_ratio: {
    title: "สัดส่วนการพูดเลียนเสียง (Ratio)",
    clinical_meaning: "สัดส่วนการพูดเลียนเสียงทันทีเมื่อเทียบกับจำนวนประโยคสนทนาทั้งหมด",
    caveat: "บทสนทนาที่มีสั้นเกินไปอาจทำให้ค่าอัตราส่วนผันผวนสูงและเชื่อถือได้น้อย",
    group: "พฤติกรรมเฉพาะออทิสติก"
  },
  pronoun_reversal_count: {
    title: "การสลับสรรพนาม (Pronoun Rev.)",
    clinical_meaning: "การสลับการใช้คำสรรพนาม เช่น เรียกตัวเองว่า 'หนู' เป็น 'คุณ' หรือเรียกคู่สนทนาแทนตัวเอง",
    caveat: "เป็นเกณฑ์วิเคราะห์เบื้องต้น มีหลายบริบทที่การใช้สรรพนามขึ้นกับเหตุการณ์จำเพาะ จึงควรตรวจทานซ้ำ",
    group: "พฤติกรรมเฉพาะออทิสติก"
  }
};

// Custom Tooltip component for Recharts
const CustomTooltip = ({ active, payload, label, lang }: any) => {
  const isThai = lang === "TH";
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 rounded-lg border border-gray-100 shadow-md">
        {label && (
          <p className="font-semibold text-gray-700 text-xs mb-1">
            {isThai && FEATURE_TRANSLATIONS[label] ? FEATURE_TRANSLATIONS[label].title : label}
          </p>
        )}
        {payload.map((item: any, index: number) => {
          let name = item.name;
          if (isThai) {
            if (name === "Importance") name = "ระดับความสำคัญ";
            else if (name === "Contribution") name = "น้ำหนักผลกระทบ (Risk Weight)";
            else if (name === "Start Profile" || name === "Start") name = "ประวัติเริ่มต้น (Baseline)";
            else if (name === "End Profile" || name === "End") name = "ประวัติปลายทาง (Outcome)";
            else if (name === "male") name = "เพศชาย";
            else if (name === "female") name = "เพศหญิง";
            else if (name === "count" || name === "Children" || name === "จำนวนเด็ก") name = "จำนวนเด็ก";
            else if (name === "observed_rate" || name === "Observed Rate") name = "อัตราสังเกตพบจริง";
            else if (name === "predicted_mean" || name === "Perfect Calibration") name = "การปรับเทียบแบบสมบูรณ์";
            else if (name === "model_net_benefit" || name === "Screening Pipeline (LogReg)") name = "ระบบช่วยคัดกรอง (LogReg)";
            else if (name === "treat_all_net_benefit" || name === "Treat All (Refer All)") name = "ส่งต่อเด็กทั้งหมด";
            else if (name === "treat_none_net_benefit" || name === "Treat None (Refer None)") name = "ไม่ส่งต่อใครเลย";
            else if (name === "ASD") name = "กลุ่มเสี่ยงออทิสติก (ASD)";
            else if (name === "TD") name = "ปกติ (TD)";
            else if (name === "DD") name = "พัฒนาการล่าช้า (DD)";
          }
          return (
            <p key={index} className="text-xs" style={{ color: item.color || item.fill || "#374151" }}>
              <span className="font-medium">{name}: </span>
              {typeof item.value === "number" ? item.value.toLocaleString() : item.value}
            </p>
          );
        })}
      </div>
    );
  }
  return null;
};

// Custom Y-axis tick renderer for horizontal charts to prevent overlapping and look beautiful
const CustomYAxisTick = (props: any) => {
  const { x, y, payload } = props;
  if (!payload || !payload.value) return null;
  const value = payload.value;
  
  // Format the label nicely. If it has a parentheses, split it.
  let primaryLabel = value;
  let subLabel = "";
  
  if (value.includes(" (")) {
    const parts = value.split(" (");
    primaryLabel = parts[0];
    subLabel = `(${parts[1]}`;
  }

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={-8}
        y={0}
        textAnchor="end"
        className="font-sans fill-gray-700"
      >
        <tspan x={-8} dy="-2" fontSize={10} fontWeight={600}>{primaryLabel}</tspan>
        {subLabel && (
          <tspan x={-8} dy="11" fontSize={8} fontWeight={400} className="fill-gray-400 italic">{subLabel}</tspan>
        )}
      </text>
    </g>
  );
};

// 1. Hero Overview Section
export const HeroSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  return (
    <div className="space-y-8 animate-fade-in">
      <div className="bg-gradient-to-r from-pastel-blue via-pastel-purple to-pastel-peach p-8 rounded-3xl relative overflow-hidden shadow-xs border border-white/60">
        {/* Abstract background shapes */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/20 rounded-full blur-3xl -mr-20 -mt-20"></div>
        <div className="absolute bottom-0 left-1/3 w-96 h-96 bg-pastel-green/20 rounded-full blur-3xl -mb-48"></div>

        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 bg-white/80 backdrop-blur-md px-3 py-1 rounded-full text-xs font-medium text-clinical-blue shadow-xs">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            {isThai ? "แพลตฟอร์มสนับสนุนการคัดกรอง" : "Decision-Support Platform"}
          </div>

          <h1 className="text-4xl md:text-5xl font-display font-semibold text-gray-900 leading-tight">
            {isThai 
              ? "ปัญญาประดิษฐ์ช่วยคัดกรองและติดตามพัฒนาการภาษาและการพูดในภาวะออทิสติก" 
              : "AI-Assisted ASD Speech-Language Screening & Monitoring"}
          </h1>

          <p className="text-base text-gray-600 leading-relaxed max-w-2xl">
            {isThai ? (
              <>
                <strong>asd-Project</strong> คือระบบสนับสนุนการตัดสินใจทางคลินิกยุคใหม่ที่ออกแบบมาเพื่อช่วยนักแก้ไขการพูด ครูผู้สอน และนักวิจัย โดยการวิเคราะห์ลักษณะการออกเสียงและการสนทนาที่สำคัญของเด็กเพื่อระบุสัญญาณความเสี่ยงตั้งแต่เนิ่นๆ และติดตามการพัฒนาการของเด็กตามช่วงเวลา
              </>
            ) : (
              <>
                <strong>asd-Project</strong> is a modern clinical decision-support ecosystem designed to assist speech-language therapists, educators, and researchers. By analyzing key child-vocalization and conversational features, it flags clinical signals early and tracks child development trajectories over time.
              </>
            )}
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <div className="flex items-center gap-2 bg-white/60 px-4 py-2.5 rounded-2xl border border-white text-xs font-medium text-gray-700 shadow-xs">
              <ShieldCheck className="w-4 h-4 text-clinical-green" />
              {isThai ? "สนับสนุนการคัดกรองเท่านั้น" : "Screening Support Only"}
            </div>
            <div className="flex items-center gap-2 bg-white/60 px-4 py-2.5 rounded-2xl border border-white text-xs font-medium text-gray-700 shadow-xs">
              <UserCheck className="w-4 h-4 text-clinical-purple" />
              {isThai ? "ขั้นตอนที่ผู้เชี่ยวชาญควบคุมดูแล" : "Human-in-the-Loop Workflow"}
            </div>
            <div className="flex items-center gap-2 bg-white/60 px-4 py-2.5 rounded-2xl border border-white text-xs font-medium text-gray-700 shadow-xs">
              <Activity className="w-4 h-4 text-clinical-blue" />
              {isThai ? "การติดตามพัฒนาการระยะยาว" : "Progress Trajectory Tracking"}
            </div>
          </div>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: isThai ? "ขนาดชุดข้อมูล" : "Active Dataset Size", value: isThai ? "เด็ก 86 คน" : "86 Children", desc: isThai ? "กลุ่มประชากรสอดคล้องมาตรฐาน TalkBank" : "Consolidated corpora matching TalkBank", color: "bg-pastel-blue/40", icon: Database },
          { title: isThai ? "ความแม่นยำการคัดกรอง" : "Screening Accuracy", value: "86.9%", desc: isThai ? "โมเดล Logistic Regression แบบสุ่มแบ่งกลุ่ม" : "Cross-validated Logistic Regression", color: "bg-pastel-purple/40", icon: Activity },
          { title: isThai ? "คุณลักษณะที่ใช้วิเคราะห์" : "Speech Features Coded", value: isThai ? "14 พารามิเตอร์" : "14 Parameters", desc: isThai ? "สกัดอัตโนมัติจากบทถอดเสียง CHAT" : "Automated CHAT transcript parsing", color: "bg-pastel-green/40", icon: Layers },
          { title: isThai ? "บันทึกการติดตามผล" : "Longitudinal Records", value: isThai ? "105+ เซสชัน" : "105+ Sessions", desc: isThai ? "ติดตามพัฒนาการเด็ก 10 คน ระยะเวลา 3 ปี" : "10 children tracked over 3 years", color: "bg-pastel-peach/40", icon: Clock },
        ].map((card, idx) => (
          <div key={idx} className={`${card.color} p-6 rounded-2xl border border-white/40 flex flex-col justify-between shadow-xs hover:scale-102 transition-transform duration-200`}>
            <div className="flex justify-between items-start">
              <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">{card.title}</span>
              <card.icon className="w-5 h-5 text-gray-600" />
            </div>
            <div className="mt-4">
              <h3 className="text-2xl font-bold text-gray-900">{card.value}</h3>
              <p className="text-xs text-gray-500 mt-1">{card.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// 2. Problem and Clinical Context Section
export const ProblemSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {isThai ? "ปัญหาและบริบททางคลินิก" : "Problem & Clinical Context"}
        </h2>
        <p className="text-sm text-gray-500">
          {isThai 
            ? "ความท้าทายในระบบสาธารณสุขที่เป็นแรงผลักดันให้ต้องพัฒนาการคัดกรองภาษาและการพูดตั้งแต่เนิ่นๆ" 
            : "The healthcare challenges driving early developmental speech screening"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-pastel-pink text-red-500"><AlertTriangle className="w-4 h-4" /></span>
            {isThai ? "อุปสรรคทางคลินิก" : "The Clinical Barriers"}
          </h3>
          <ul className="space-y-3.5 text-sm text-gray-600">
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-pastel-pink mt-2 shrink-0" />
              <span>
                {isThai ? (
                  <>
                    <strong>การประเมินที่ล่าช้า:</strong> อายุเฉลี่ยที่ได้รับการวินิจฉัยภาวะออทิสติกมักจะเกิน 4 ปี ซึ่งพลาดโอกาสทองของการกระตุ้นพัฒนาการในช่วงสมองกำลังพัฒนาอย่างรวดเร็ว (อายุ 1.5 - 3 ปี)
                  </>
                ) : (
                  <>
                    <strong>Delayed Clinical Review:</strong> Many children do not receive specialist developmental review until after age 4, missing the early neural plasticity window (ages 1.5 - 3).
                  </>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-pastel-pink mt-2 shrink-0" />
              <span>
                {isThai ? (
                  <>
                    <strong>ความขาดแคลนผู้เชี่ยวชาญ:</strong> กุมารแพทย์และนักแก้ไขการพูด (SLP) ต้องเผชิญกับภาระงานล้นมือและคิวยาวมาก ทำให้กระบวนการวินิจฉัยล่าช้าออกไปหลายเดือน
                  </>
                ) : (
                  <>
                    <strong>Specialist Scarcity:</strong> Pediatricians and speech-language pathologists (SLPs) face massive backlogs, delaying qualified clinical review.
                  </>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-pastel-pink mt-2 shrink-0" />
              <span>
                {isThai ? (
                  <>
                    <strong>การคัดกรองที่มีความลำเอียง:</strong> แบบสอบถามผู้ปกครองแบบดั้งเดิม (เช่น M-CHAT) พึ่งพาการจำย้อนหลังซึ่งอาจขาดความเที่ยงตรงและเกิดความลำเอียงทางความคิดได้ง่าย
                  </>
                ) : (
                  <>
                    <strong>Subjective Screening:</strong> Traditional parent questionnaires (like M-CHAT) rely heavily on subjective recalls and are prone to cognitive bias.
                  </>
                )}
              </span>
            </li>
          </ul>
        </div>

        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-pastel-green text-green-600"><CheckCircle className="w-4 h-4" /></span>
            {isThai ? "แนวทางสนับสนุนการตัดสินใจของเรา" : "Our Decision Support Solution"}
          </h3>
          <ul className="space-y-3.5 text-sm text-gray-600">
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-pastel-green mt-2 shrink-0" />
              <span>
                {isThai ? (
                  <>
                    <strong>การวัดผลเชิงวัตถุ:</strong> ประเมินความซับซ้อนของไวยากรณ์ (MLU) ความหลากหลายของคำศัพท์ (TTR) และสัญญาณพฤติกรรมพูดคุยตามจริงโดยสกัดจากบทถอดเทปเสียงโดยตรง
                  </>
                ) : (
                  <>
                    <strong>Objective Quantities:</strong> Measures language complexity (MLU), vocabulary diversity (TTR), and pragmatic patterns directly from speech transcripts.
                  </>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-pastel-green mt-2 shrink-0" />
              <span>
                {isThai ? (
                  <>
                    <strong>เพิ่มประสิทธิภาพของนักบำบัด:</strong> ทดแทนขั้นตอนถอดความและจดบันทึกด้วยมือที่น่าเบื่อหน่าย ด้วยระบบสกัดฟีเจอร์ AI อัตโนมัติ ช่วยประหยัดเวลาการทำงานหลายชั่วโมงต่อเด็กหนึ่งคน
                  </>
                ) : (
                  <>
                    <strong>Clinical Efficiency:</strong> Replaces tedious manual speech-sample coding with an automated parsing pipeline, saving therapists hours per child.
                  </>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-pastel-green mt-2 shrink-0" />
              <span>
                {isThai ? (
                  <>
                    <strong>ติดตามผลพัฒนาการอย่างต่อเนื่อง:</strong> รองรับการติดตามพัฒนาการของเด็กแต่ละคนแบบระยะยาว เพื่อบันทึกความก้าวหน้าตลอดหลายเดือนเพื่อใช้ปรับปรุงแนวทางการบำบัดภาษา
                  </>
                ) : (
                  <>
                    <strong>Continuous Monitoring:</strong> Supports regular progress reviews, capturing developmental changes over months to guide speech therapy.
                  </>
                )}
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

// 3. System Architecture Section
export const ArchitectureSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  const steps = [
    { num: "01", name: isThai ? "อัปโหลดเสียงบันทึก" : "Recording Upload", desc: isThai ? "อัปโหลดเสียงบันทึกขณะเด็กเล่นบทสนทนา 10-20 นาทีอย่างปลอดภัยและเป็นความลับ" : "10-20 min play session audio uploaded securely.", color: "bg-pastel-blue text-clinical-blue", icon: Play },
    { num: "02", name: isThai ? "แยกเสียงและถอดความ" : "Diarization & ASR", desc: isThai ? "Whisper แปลงข้อความของเด็กและนักบำบัด และระบบแยกลักษณะเสียงคนพูดเพื่อระบุตัวตน" : "Whisper transcribes child/adult; diarizer segments voices.", color: "bg-pastel-purple text-clinical-purple", icon: MessageSquare },
    { num: "03", name: isThai ? "จัดรูปแบบรหัส CHAT" : "CHAT & pylangacq", desc: isThai ? "จัดเก็บและถอดคำพูดตามมาตรฐานโครงสร้างรหัสภาษาศาสตร์ CHAT เพื่อนำไปประมวลผลต่อ" : "Transcripts structured to standard clinical CHAT formatting.", color: "bg-pastel-peach text-clinical-peach", icon: FileText },
    { num: "04", name: isThai ? "สกัดคุณลักษณะภาษา" : "Feature Extraction", desc: isThai ? "ระบบประมวลผลสกัดฟีเจอร์พารามิเตอร์ภาษา 14 รายการ เช่น MLU, TTR, เลียนเสียงพูด, การสลับสรรพนาม" : "Extracts 14 language metrics (MLU, TTR, Echolalia, Reversals).", color: "bg-pastel-green text-clinical-green", icon: Layers },
    { num: "05", name: isThai ? "คำนวณและประเมินผล" : "Risk Indicator", desc: isThai ? "แบบจำลอง Logistic Regression คำนวณความน่าจะเป็นของสัญญาณความเสี่ยงและกำหนดระดับความไม่แน่นอน" : "Logistic Regression model estimates probability & uncertainty.", color: "bg-pastel-pink text-red-500", icon: Activity },
    { num: "06", name: isThai ? "พอร์ทัลผู้ประเมิน" : "Clinician Portal", desc: isThai ? "นักแก้ไขการพูดร่วมตรวจทานบทสนทนา แก้ไขคำผิด ลงความเห็น และสั่งพิมพ์รายงานคัดกรองออกมา" : "Therapist audits transcripts, validates signals, and exports report.", color: "bg-pastel-yellow text-amber-600", icon: UserCheck },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {isThai ? "สถาปัตยกรรมระบบ" : "System Architecture"}
        </h2>
        <p className="text-sm text-gray-500">
          {isThai 
            ? "ขั้นตอนการทำงานของระบบคัดกรองสัญญาณความเสี่ยงภาษาและการพูดในเด็กเชิงรุก" 
            : "Pipeline map of the speech-language AI decision-support platform"}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {steps.map((step, idx) => (
          <div key={idx} className="glass-card p-6 rounded-2xl flex flex-col justify-between border border-gray-100 relative overflow-hidden group hover:shadow-md transition-shadow">
            <div className="absolute top-0 right-0 w-16 h-16 bg-gray-50 rounded-bl-full flex items-center justify-center font-display font-bold text-gray-300 text-sm group-hover:bg-white transition-colors">
              {step.num}
            </div>
            <div className="space-y-4">
              <span className={`inline-flex p-2.5 rounded-xl ${step.color}`}>
                <step.icon className="w-5 h-5" />
              </span>
              <div>
                <h3 className="font-semibold text-gray-900 text-base">{step.name}</h3>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{step.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// 4. Dataset Overview Section
export const DatasetSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  const classDist = projectData.class_distribution;
  const ageDist = projectData.age_distribution;
  const sexDist = projectData.sex_distribution;
  const rawRecords = projectData.dataset_records || [];

  // Search & Filter State
  const [searchTerm, setSearchTerm] = useState("");
  const [corpusFilter, setCorpusFilter] = useState("All");
  const [groupFilter, setGroupFilter] = useState("All");
  const [sexFilter, setSexFilter] = useState("All");

  // Filtering Logic
  const filteredRecords = rawRecords.filter((record: any) => {
    const matchesSearch = record.participant_id.toString().includes(searchTerm);
    const matchesCorpus = corpusFilter === "All" || record.corpus === corpusFilter;
    const matchesGroup = groupFilter === "All" || record.group === groupFilter;
    const matchesSex = sexFilter === "All" || record.sex === sexFilter;
    return matchesSearch && matchesCorpus && matchesGroup && matchesSex;
  });

  const getGroupName = (name: string) => {
    if (!isThai) return name;
    if (name === "ASD") return "เสี่ยงออทิสติก";
    if (name === "TD" || name === "Typically Developing (TD)") return "ปกติ (TD)";
    if (name === "DD" || name === "Developmental Delay (DD)") return "พัฒนาการล่าช้า (DD)";
    return name;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {isThai ? "ภาพรวมชุดข้อมูล" : "Dataset Overview"}
        </h2>
        <p className="text-sm text-gray-500">
          {isThai 
            ? "ข้อมูลเชิงลึกของกลุ่มเด็กทดสอบตามมาตรฐาน TalkBank (n = 86)" 
            : "Granular profile of child cohorts matching TalkBank standards (n = 86)"}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Class Distribution */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
            {isThai ? "การกระจายกลุ่มอาการ" : "Class Distribution"}
          </h3>
          <div className="h-48 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={classDist}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {classDist.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color || Object.values(PASTEL_COLORS)[index % 6]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip lang={lang} />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute text-center">
              <span className="block text-2xl font-bold text-gray-800">86</span>
              <span className="text-[10px] text-gray-400 font-medium uppercase">
                {isThai ? "กลุ่มทดสอบทั้งหมด" : "Total Cohort"}
              </span>
            </div>
          </div>
          <div className="space-y-1.5 text-xs">
            {classDist.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center text-gray-600">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  {getGroupName(item.name)}
                </span>
                <span className="font-semibold">{item.value} {isThai ? "คน" : "children"}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Age Distribution */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between col-span-1 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
            {isThai ? "การกระจายตามช่วงอายุ" : "Age Distribution"}
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ageDist} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <XAxis dataKey="range" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip lang={lang} />} />
                <Bar dataKey="count" fill={PASTEL_COLORS.purple} radius={[4, 4, 0, 0]} name={isThai ? "จำนวนเด็ก" : "Children"} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-gray-500 leading-relaxed mt-2">
            {isThai 
              ? "ชุดข้อมูลนี้มีความหนาแน่นสูงในกลุ่มเด็กปฐมวัย (36-59 เดือน) ซึ่งเป็นหน้าต่างวัยทองที่มีความสำคัญที่สุดสำหรับการเข้าประเมินและช่วยเหลือระยะเริ่มแรก" 
              : "The dataset features a high concentration of children in critical preschool ages (36-59 months), which are the primary windows for speech therapy interventions and early developmental assessments."}
          </div>
        </div>
      </div>

      {/* Sex and Corpora Mix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-6 rounded-2xl flex items-center justify-between">
          <div className="space-y-3 max-w-[55%]">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
              {isThai ? "การกระจายทางเพศ" : "Sex Distribution"}
            </h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              {isThai 
                ? "เด็กชายมีสัดส่วนค่อนข้างสูงในชุดข้อมูล (อัตราส่วน 3:1) ซึ่งสอดคล้องกับอุบัติการณ์ของภาวะออทิสติกที่พบในเพศชายได้มากกว่าตามข้อมูลระบาดวิทยา" 
                : "Male children are represented heavily in the dataset (3:1 ratio), reflecting the higher prevalence of ASD diagnoses in males reported in epidemiological literature."}
            </p>
            <div className="text-xs space-y-1">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-pastel-blue" />
                <span>{isThai ? "เพศชาย" : "Male"}: {sexDist[0]?.value} (75%)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-pastel-pink" />
                <span>{isThai ? "เพศหญิง" : "Female"}: {sexDist[1]?.value} (25%)</span>
              </div>
            </div>
          </div>
          <div className="h-32 w-32">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sexDist}
                  cx="50%"
                  cy="50%"
                  outerRadius={50}
                  innerRadius={30}
                  dataKey="value"
                >
                  <Cell fill={PASTEL_COLORS.blue} name="male" />
                  <Cell fill={PASTEL_COLORS.pink} name="female" />
                </Pie>
                <Tooltip content={<CustomTooltip lang={lang} />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
            {isThai ? "สัดส่วนคลังข้อมูลพัฒนาการ" : "Development Corpora Mix"}
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {projectData.corpus_distribution.map((corpus, idx) => (
              <div key={idx} className="bg-white p-3 rounded-xl border border-gray-50 shadow-2xs">
                <span className="text-[10px] text-gray-400 font-semibold uppercase block">{corpus.name}</span>
                <span className="text-xl font-bold text-gray-800">
                  {corpus.count} <span className="text-xs font-normal text-gray-400">{isThai ? "ราย" : "cases"}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Comprehensive Child Dataset Explorer */}
      <div className="glass-card p-6 rounded-3xl space-y-6">
        <div className="flex justify-between items-center flex-wrap gap-4 border-b border-gray-50 pb-4">
          <div>
            <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-clinical-blue" />
              {isThai ? "เครื่องมือสำรวจข้อมูลกลุ่มทางคลินิก" : "Clinical Cohort Data Explorer"}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              {isThai ? `สำรวจพารามิเตอร์ตามจริงของเด็กทั้งหมด ${rawRecords.length} คน` : `Explore real parameters for all ${rawRecords.length} children`}
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs font-medium">
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
              <Search className="w-3.5 h-3.5" />
            </span>
            <input
              type="text"
              placeholder={isThai ? "ค้นหาไอดีเด็ก..." : "Search ID..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-clinical-blue text-gray-700 font-semibold"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <select
              value={corpusFilter}
              onChange={(e) => setCorpusFilter(e.target.value)}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-2 py-2 focus:outline-none focus:border-clinical-blue text-gray-600 font-semibold cursor-pointer"
            >
              <option value="All">{isThai ? "คลังข้อมูลทั้งหมด" : "All Corpora"}</option>
              {Array.from(new Set(rawRecords.map((r: any) => r.corpus))).map((c: any) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-clinical-blue text-gray-600 font-semibold cursor-pointer"
          >
            <option value="All">{isThai ? "ทุกการวินิจฉัย" : "All Diagnoses"}</option>
            <option value="ASD">{isThai ? "กลุ่มเสี่ยงออทิสติก (ASD)" : "ASD"}</option>
            <option value="TD">{isThai ? "พัฒนาการตามวัย (TD)" : "Typically Developing (TD)"}</option>
            <option value="DD">{isThai ? "พัฒนาการล่าช้า (DD)" : "Developmental Delay (DD)"}</option>
          </select>

          <select
            value={sexFilter}
            onChange={(e) => setSexFilter(e.target.value)}
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-clinical-blue text-gray-600 font-semibold cursor-pointer"
          >
            <option value="All">{isThai ? "ทุกเพศ" : "All Sexes"}</option>
            <option value="male">{isThai ? "เพศชาย" : "Male"}</option>
            <option value="female">{isThai ? "เพศหญิง" : "Female"}</option>
          </select>
        </div>

        {/* Data Table */}
        <div className="overflow-hidden border border-gray-100 rounded-2xl">
          <div className="max-h-80 overflow-y-auto overflow-x-auto custom-scrollbar">
            <table className="min-w-[960px] divide-y divide-gray-100 text-left text-xs text-gray-500">
              <thead className="bg-gray-50 text-[10px] text-gray-400 font-bold uppercase tracking-wider sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 bg-gray-50 whitespace-nowrap">{isThai ? "ไอดีเด็ก" : "Child ID"}</th>
                  <th className="px-4 py-3 bg-gray-50 whitespace-nowrap">{isThai ? "คลังข้อมูล" : "Corpus"}</th>
                  <th className="px-4 py-3 bg-gray-50 whitespace-nowrap">{isThai ? "กลุ่มอาการ" : "Group"}</th>
                  <th className="px-4 py-3 bg-gray-50 whitespace-nowrap">{isThai ? "เพศ" : "Sex"}</th>
                  <th className="px-4 py-3 bg-gray-50 whitespace-nowrap">{isThai ? "อายุ (เดือน)" : "Age (mo)"}</th>
                  <th className="px-4 py-3 bg-gray-50 text-right whitespace-nowrap">{isThai ? "จำนวนประโยค" : "Utterances"}</th>
                  <th className="px-4 py-3 bg-gray-50 text-right whitespace-nowrap">MLU</th>
                  <th className="px-4 py-3 bg-gray-50 text-right whitespace-nowrap">TTR</th>
                  <th className="px-4 py-3 bg-gray-50 text-right whitespace-nowrap">{isThai ? "อัตราการพูดไม่ชัด" : "Unintelligible Ratio"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white font-medium text-gray-700">
                {filteredRecords.length > 0 ? (
                  filteredRecords.map((record: any, idx: number) => (
                    <tr key={idx} className="hover:bg-gray-50/50">
                      <td className="px-4 py-3 font-bold text-gray-900 whitespace-nowrap">{record.participant_id}</td>
                      <td className="px-4 py-3 text-gray-400 uppercase text-[10px] whitespace-nowrap">{record.corpus}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold whitespace-nowrap ${
                          record.group === "ASD" ? "bg-pastel-blue text-clinical-blue" :
                          record.group === "TD" ? "bg-pastel-green text-clinical-green" :
                          "bg-pastel-pink text-red-600"
                        }`}>
                          {getGroupName(record.group)}
                        </span>
                      </td>
                      <td className="px-4 py-3 capitalize text-gray-500 whitespace-nowrap">
                        {isThai ? (record.sex === "male" ? "ชาย" : "หญิง") : record.sex}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">{record.age_months ? record.age_months.toFixed(1) : "—"}</td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">{record.total_utterances || "—"}</td>
                      <td className="px-4 py-3 text-right font-bold whitespace-nowrap">{record.mlu ? record.mlu.toFixed(2) : "—"}</td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">{record.ttr ? record.ttr.toFixed(3) : "—"}</td>
                      <td className="px-4 py-3 text-right text-gray-400 whitespace-nowrap">{record.unintelligible_ratio ? `${(record.unintelligible_ratio * 100).toFixed(1)}%` : "0.0%"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                      {isThai ? "ไม่พบข้อมูลเด็กที่ตรงตามเงื่อนไข" : "No cohort records found matching filters."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="text-[10px] text-gray-400 text-right font-medium">
          {isThai 
            ? `แสดง ${filteredRecords.length} จากทั้งหมด ${rawRecords.length} รายการ`
            : `Showing ${filteredRecords.length} of ${rawRecords.length} records`}
        </div>
      </div>
    </div>
  );
};

// 5. Feature Dashboard Section
export const FeatureSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  const [selectedGroup, setSelectedGroup] = useState<string>("All");
  const schema = projectData.feature_schema;

  // Group translations helper
  const getGroupNameTranslation = (groupName: string) => {
    if (!isThai) return groupName;
    if (groupName === "Demographics") return "ประชากรศาสตร์";
    if (groupName === "Productivity") return "ปริมาณการพูด";
    if (groupName === "Complexity") return "ความซับซ้อนโครงสร้าง";
    if (groupName === "Lexical diversity") return "ความหลากหลายคำศัพท์";
    if (groupName === "ASD-relevant markers") return "พฤติกรรมเฉพาะออทิสติก";
    if (groupName === "Pragmatic") return "การสื่อสารทางสังคม";
    return groupName;
  };

  const groups = ["All", ...Array.from(new Set(schema.map((item) => item.group)))];
  const filteredSchema = selectedGroup === "All" ? schema : schema.filter((item) => item.group === selectedGroup);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {isThai ? "สารบัญคุณลักษณะภาษาและการพูด" : "Feature Dashboard"}
        </h2>
        <p className="text-sm text-gray-500">
          {isThai 
            ? "ทำเนียบพารามิเตอร์เชิงลึกทางภาษาศาสตร์และการบำบัดรักษาที่สกัดได้จากบทถอดเสียงสนทนา" 
            : "Detailed directory of clinical speech-language features parsed from transcripts"}
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {groups.map((group, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedGroup(group)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              selectedGroup === group
                ? "bg-pastel-blue text-clinical-blue border border-clinical-blue/20"
                : "bg-white text-gray-500 hover:text-gray-700 border border-gray-200/60"
            }`}
          >
            {isThai ? (group === "All" ? "ทั้งหมด" : getGroupNameTranslation(group)) : group}
          </button>
        ))}
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredSchema.map((item: any, idx: number) => {
          let cardBg = "bg-white";
          let tagColor = "bg-gray-100 text-gray-600";
          if (item.group === "Complexity") {
            cardBg = "hover:bg-pastel-blue/10";
            tagColor = "bg-pastel-blue text-clinical-blue";
          } else if (item.group === "Lexical diversity") {
            cardBg = "hover:bg-pastel-purple/10";
            tagColor = "bg-pastel-purple text-clinical-purple";
          } else if (item.group === "ASD-relevant markers") {
            cardBg = "hover:bg-pastel-pink/10";
            tagColor = "bg-pastel-pink text-red-600";
          } else if (item.group === "Pragmatic") {
            cardBg = "hover:bg-pastel-peach/10";
            tagColor = "bg-pastel-peach text-clinical-peach";
          }

          // Use FEATURE_TRANSLATIONS for Thai texts if available
          const translation = isThai ? FEATURE_TRANSLATIONS[item.feature] : null;
          const titleText = translation ? translation.title : item.title;
          const clinicalMeaningText = translation ? translation.clinical_meaning : item.clinical_meaning;
          const caveatText = translation ? translation.caveat : item.caveat;

          return (
            <div
              key={idx}
              className={`glass-card p-6 rounded-2xl border border-gray-100 flex flex-col justify-between transition-all duration-200 ${cardBg}`}
            >
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-base">{titleText}</h3>
                    <code className="text-[10px] text-gray-400 mt-1 block">{item.feature}</code>
                  </div>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full uppercase tracking-wider ${tagColor}`}>
                    {getGroupNameTranslation(item.group)}
                  </span>
                </div>

                <div className="text-xs text-gray-600 space-y-2 pt-1.5">
                  <p><strong>{isThai ? "ความหมายทางคลินิก:" : "Clinical Meaning:"}</strong> {clinicalMeaningText}</p>
                  <p><strong>{isThai ? "สูตรคำนวณ/การสกัดฟีเจอร์:" : "Formula/Measurement:"}</strong> <span className="bg-gray-50 px-1.5 py-0.5 rounded font-mono text-[10px] border border-gray-100">{item.formula}</span></p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-50 flex items-start gap-1.5 text-[11px] text-amber-600">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span className="leading-normal"><strong>{isThai ? "ข้อควรระวัง:" : "Caveat:"}</strong> {caveatText}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// 6. Model Performance Section
// 6. Model Performance Section
export const PerformanceSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  const [activeTab, setActiveTab] = useState<"summary" | "curves" | "matrix" | "loco" | "subgroups">("summary");
  const comparison = projectData.model_comparison;
  const roc = projectData.roc_curve;
  const pr = projectData.pr_curve;
  const calibration = projectData.calibration;
  const subgroups = projectData.subgroup_performance;
  const dca = (projectData as any).decision_curve || [];
  const loco = (projectData as any).leave_one_corpus_out || [];

  const getTaskLabel = (taskName: string) => {
    if (!isThai) return taskName;
    if (taskName === "binary") return "สองกลุ่ม (ASD/TD)";
    if (taskName === "multi") return "สามกลุ่ม (ASD/TD/DD)";
    return taskName;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {isThai ? "ประสิทธิภาพของโมเดล" : "Model Performance"}
        </h2>
        <p className="text-sm text-gray-500">
          {isThai 
            ? "ผลการทดสอบประสิทธิภาพแบบประเมินข้ามกลุ่ม ผลประโยชน์ทางคลินิก และการทดสอบความคงเส้นคงวาข้ามชุดข้อมูล" 
            : "Cross-validated benchmark results, clinical review utility, and cross-corpus audits"}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100 overflow-x-auto scrollbar-none">
        {[
          { id: "summary", label: isThai ? "การเปรียบเทียบโมเดล" : "Model Comparison" },
          { id: "curves", label: isThai ? "ROC, PR และการปรับเทียบ" : "ROC, PR & Calibration" },
          { id: "matrix", label: isThai ? "ตาราง Confusion Matrix" : "Confusion Matrix" },
          { id: "loco", label: isThai ? "การทดสอบข้ามคลังข้อมูล (LOCO)" : "Cross-Corpus Validation (LOCO)" },
          { id: "subgroups", label: isThai ? "การวิเคราะห์กลุ่มประชากรย่อย" : "Subgroup Auditing" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 text-xs font-semibold -mb-px border-b-2 transition-all shrink-0 ${
              activeTab === tab.id
                ? "border-clinical-blue text-clinical-blue"
                : "border-transparent text-gray-400 hover:text-gray-600"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === "summary" && (
        <div className="space-y-6">
          {/* Comparative Table */}
          <div className="glass-card rounded-2xl overflow-hidden border border-gray-100">
            <div className="overflow-x-auto">
              <table className="min-w-[960px] divide-y divide-gray-100 text-left text-xs text-gray-500">
                <thead className="bg-gray-50 text-[10px] text-gray-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "แบบจำลอง (Model)" : "Model Name"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "ภารกิจ (Task)" : "Task"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "ความถูกต้อง (Accuracy)" : "Accuracy"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "F1 Macro" : "F1 Macro"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">ROC AUC</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "ความไว (Sensitivity)" : "Sensitivity"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "ความจำเพาะ (Specificity)" : "Specificity"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "ความแม่นยำ (PPV)" : "PPV (Precision)"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">NPV</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white font-medium text-gray-700">
                  {comparison.map((model: any, idx: number) => (
                    <tr key={idx} className={model.model === "LogReg" && model.task === "binary" ? "bg-pastel-blue/20" : ""}>
                      <td className="px-6 py-4 flex items-center gap-1.5 font-bold whitespace-nowrap">
                        {model.model === "LogReg" && model.task === "binary" && (
                          <span className="w-1.5 h-1.5 rounded-full bg-clinical-blue" />
                        )}
                        {model.model} {model.model === "LogReg" && model.task === "binary" && <span className="text-[9px] font-normal text-clinical-blue px-1.5 py-0.5 rounded-full bg-pastel-blue border border-clinical-blue/20 whitespace-nowrap">{isThai ? "เลือกใช้งาน" : "Selected"}</span>}
                      </td>
                      <td className="px-6 py-4 font-normal text-gray-400 capitalize whitespace-nowrap">{getTaskLabel(model.task)}</td>
                      <td className="px-6 py-4 font-bold whitespace-nowrap">{(model.accuracy * 100).toFixed(1)}%</td>
                      <td className="px-6 py-4 whitespace-nowrap">{(model.f1_macro * 100).toFixed(1)}%</td>
                      <td className="px-6 py-4 whitespace-nowrap">{model.roc_auc ? (model.roc_auc).toFixed(3) : "—"}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{model.sensitivity ? `${(model.sensitivity * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{model.specificity ? `${(model.specificity * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{model.ppv ? `${(model.ppv * 100).toFixed(0)}%` : "—"}</td>
                      <td className="px-6 py-4 whitespace-nowrap">{model.npv ? `${(model.npv * 100).toFixed(0)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-pastel-blue/30 p-5 rounded-2xl border border-clinical-blue/10 space-y-2">
              <h4 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-clinical-blue" /> {isThai ? "ทำไมถึงเลือก Logistic Regression?" : "Why Logistic Regression?"}
              </h4>
              <p className="text-xs text-gray-600 leading-relaxed">
                {isThai ? (
                  <>
                    เราเลือกใช้ <strong>Logistic Regression (LogReg)</strong> เป็นแบบจำลองการคัดกรองหลักแทน Random Forest หรือ SVM แม้ว่าค่าประสิทธิภาพบางตัวอาจใกล้เคียงกัน แต่ Logistic Regression ให้ผลลัพธ์เป็นค่าความน่าจะเป็นที่อธิบายและแยกแยะทิศทางผลกระทบของฟีเจอร์ได้โดยตรง ช่วยให้นักบำบัดรักษาแกะรอยน้ำหนักค่าสัมประสิทธิ์ของฟีเจอร์ (Coefficients) เพื่ออธิบายทิศทางความเสี่ยงได้ชัดเจนทางคลินิก
                  </>
                ) : (
                  <>
                    We selected <strong>Logistic Regression (LogReg)</strong> as our primary screening support model over Random Forest and SVM. Despite similar or slightly higher metrics, Logistic Regression yields direct probability outputs that are fully interpretable, allowing clinicians to trace feature coefficients and calculate risk bounds.
                  </>
                )}
              </p>
            </div>
            
            <div className="bg-pastel-green/20 p-6 rounded-2xl border border-clinical-green/10 space-y-4">
              <div>
                <h4 className="font-semibold text-gray-800 text-sm flex items-center gap-2">
                  <Users className="w-4 h-4 text-clinical-green" /> {isThai ? "ระดับความสำคัญของคุณลักษณะทั้งหมด" : "Complete Feature Importance Profile"}
                </h4>
                <p className="text-[10px] text-gray-400 mt-1">
                  {isThai 
                    ? `ค่าเฉลี่ยความสําคัญในการจำแนกกลุ่มอาการของเด็ก (MDI) สำหรับพารามิเตอร์ทั้งหมด ${projectData.feature_importance.length} รายการ`
                    : `MDI (Mean Decrease in Impurity) values showing classification contribution for all ${projectData.feature_importance.length} features.`}
                </p>
              </div>
              <div className="h-[460px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart 
                    data={projectData.feature_importance.map((item) => ({
                      ...item,
                      title: isThai && FEATURE_TRANSLATIONS[item.feature] ? FEATURE_TRANSLATIONS[item.feature].title : item.title
                    }))} 
                    layout="vertical" 
                    margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                  >
                    <XAxis type="number" tick={{ fontSize: 9 }} />
                    <YAxis dataKey="title" type="category" tick={<CustomYAxisTick />} width={200} tickLine={false} axisLine={false} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Bar dataKey="importance" fill={PASTEL_COLORS.green} radius={[0, 4, 4, 0]} name={isThai ? "ระดับความสำคัญ" : "Importance"} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "curves" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* ROC Curve */}
            <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
              <div className="mb-2">
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
                  {isThai ? "กราฟ ROC (AUC = 0.935)" : "ROC Curve (AUC = 0.935)"}
                </h3>
                <p className="text-[10px] text-gray-400">
                  {isThai ? "สัดส่วนระหว่างความไว (Sensitivity) กับอัตราการเตือนพลาด (FPR)" : "Tradeoff between Sensitivity and False Positive Rate"}
                </p>
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={roc} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <XAxis dataKey="fpr" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
                    <YAxis dataKey="tpr" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Line dataKey="tpr" stroke={CLINICAL_COLORS.blue} strokeWidth={2} dot={{ r: 3 }} name={isThai ? "อัตราการตรวจพบจริง (TPR)" : "True Positive Rate"} />
                    <Line dataKey="fpr" stroke="#E5E7EB" strokeWidth={1} strokeDasharray="3 3" dot={false} name={isThai ? "การสุ่มทาย" : "Random Guess"} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* PR Curve */}
            <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
              <div className="mb-2">
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
                  {isThai ? "กราฟ PR (AUC = 0.952)" : "PR Curve (AUC = 0.952)"}
                </h3>
                <p className="text-[10px] text-gray-400">
                  {isThai ? "สัดส่วนระหว่างความแม่นยำทำนายบวก (PPV) และความไวความครอบคลุม (Sensitivity)" : "Tradeoff between Precision (PPV) and Recall (Sensitivity)"}
                </p>
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={pr} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <XAxis dataKey="recall" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
                    <YAxis dataKey="precision" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Line dataKey="precision" stroke={CLINICAL_COLORS.purple} strokeWidth={2} dot={{ r: 3 }} name={isThai ? "ความแม่นยำ (Precision)" : "Precision"} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Calibration Plot */}
            <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
              <div className="mb-2">
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
                  {isThai ? "กราฟการปรับเทียบ (Calibration)" : "Calibration Plot"}
                </h3>
                <p className="text-[10px] text-gray-400">
                  {isThai ? "เปรียบเทียบค่าความเสี่ยงที่คาดการณ์เฉลี่ย กับ อัตราความถี่จริงที่สังเกตได้" : "Predicted Risk Mean vs Actual Observed Rate"}
                </p>
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={calibration} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <XAxis dataKey="predicted_mean" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
                    <YAxis dataKey="observed_rate" type="number" domain={[0, 1]} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Line dataKey="observed_rate" stroke={CLINICAL_COLORS.green} strokeWidth={2} dot={{ r: 4 }} name={isThai ? "อัตราที่สังเกตพบจริง" : "Observed Rate"} />
                    <Line dataKey="predicted_mean" stroke="#E5E7EB" strokeWidth={1} strokeDasharray="3 3" dot={false} name={isThai ? "การปรับเทียบแบบสมบูรณ์" : "Perfect Calibration"} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* DCA Section */}
          {dca.length > 0 && (
            <div className="glass-card p-6 rounded-3xl">
              <div className="mb-4">
                <h3 className="text-base font-semibold text-gray-800">
                  {isThai ? "การวิเคราะห์กราฟการตัดสินใจทางคลินิก (DCA)" : "Decision Curve Analysis (DCA)"}
                </h3>
                <p className="text-xs text-gray-400">
                  {isThai 
                    ? "คำนวณผลประโยชน์สุทธิทางคลินิกเปรียบเทียบกับการส่งต่อเด็กทั้งหมด หรือ ไม่ส่งต่อใครเลย" 
                    : "Calculates net clinical benefit compared to default clinical strategies (Treat All vs. Treat None)"}
                </p>
              </div>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dca} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <XAxis dataKey="threshold" tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 10 }} />
                    <YAxis domain={[-0.1, 0.6]} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line dataKey="model_net_benefit" name={isThai ? "ระบบช่วยคัดกรอง (LogReg)" : "Screening Pipeline (LogReg)"} stroke={CLINICAL_COLORS.blue} strokeWidth={2.5} dot={false} />
                    <Line dataKey="treat_all_net_benefit" name={isThai ? "ส่งต่อเด็กทั้งหมด" : "Treat All (Refer All)"} stroke={PASTEL_COLORS.pink} strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                    <Line dataKey="treat_none_net_benefit" name={isThai ? "ไม่ส่งต่อใครเลย" : "Treat None (Refer None)"} stroke="#9CA3AF" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="text-[10px] text-gray-500 leading-relaxed mt-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <strong>{isThai ? "การแปลผลทางคลินิก:" : "Clinical Interpretation:"}</strong>{" "}
                {isThai ? (
                  <>
                    การวิเคราะห์กราฟการตัดสินใจ (DCA) แสดงให้เห็นว่าการใช้ระบบช่วยคัดกรองด้วย LogReg เพื่อจัดลำดับความจำเป็นของการส่งต่อไปประเมินเพิ่มเติม ช่วยเพิ่มผลประโยชน์สุทธิ (Net Benefit) อย่างมีนัยสำคัญในทุกช่วงของขีดจำกัดคะแนนความเสี่ยง (ตั้งแต่ 10% ถึง 80%) เมื่อเปรียบเทียบกับวิธีการส่งต่อเด็กทั้งหมดทันทีหรือการไม่ส่งต่อใครเลย วิธีนี้ช่วยประหยัดทรัพยากรการประเมินทางคลินิกที่ไม่จำเป็นลงได้อย่างมาก (ลดการเตือนหลอก) ในขณะที่รักษาระดับการคัดแยกเด็กที่มีความเสี่ยงได้อย่างครอบคลุม
                  </>
                ) : (
                  <>
                    Decision Curve Analysis shows that utilizing the LogReg screening model to triage referrals achieves a positive net benefit across all probability thresholds from 10% up to 80% compared to referring all children or referring none. This significantly reduces unnecessary clinician assessments (False Positives) while capturing at-risk children.
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "matrix" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          {/* Heatmap Confusion Matrix */}
          <div className="glass-card p-8 rounded-2xl">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-6 text-center">
              {isThai ? "ตาราง Confusion Matrix (LogReg 5-fold CV)" : "Confusion Matrix (LogReg 5-fold CV)"}
            </h3>
            <div className="grid grid-cols-3 gap-2 text-center items-center">
              {/* Row Headers */}
              <div></div>
              <div className="text-[10px] text-gray-400 font-bold uppercase">{isThai ? "ทายว่าปกติ" : "Pred non-ASD"}</div>
              <div className="text-[10px] text-gray-400 font-bold uppercase">{isThai ? "ทายว่าเสี่ยงออทิสติก" : "Pred ASD"}</div>

              <div className="text-right text-[10px] text-gray-400 font-bold uppercase pr-2">{isThai ? "ผลจริงปกติ" : "True non-ASD"}</div>
              {/* True Negative */}
              <div className="bg-pastel-blue/30 border border-white p-6 rounded-xl shadow-2xs">
                <span className="block text-2xl font-bold text-gray-800">51</span>
                <span className="text-[9px] text-gray-400 uppercase font-semibold">{isThai ? "ปกติถูกต้อง (TN)" : "True Neg (TN)"}</span>
              </div>
              {/* False Positive */}
              <div className="bg-pastel-pink/20 border border-white p-6 rounded-xl shadow-2xs">
                <span className="block text-2xl font-bold text-gray-800">6</span>
                <span className="text-[9px] text-gray-400 uppercase font-semibold">{isThai ? "เตือนหลอก (FP)" : "False Pos (FP)"}</span>
              </div>

              <div className="text-right text-[10px] text-gray-400 font-bold uppercase pr-2">{isThai ? "ผลจริงเสี่ยง" : "True ASD"}</div>
              {/* False Negative */}
              <div className="bg-pastel-pink/20 border border-white p-6 rounded-xl shadow-2xs">
                <span className="block text-2xl font-bold text-gray-800">10</span>
                <span className="text-[9px] text-gray-400 uppercase font-semibold">{isThai ? "หลุดคัดกรอง (FN)" : "False Neg (FN)"}</span>
              </div>
              {/* True Positive */}
              <div className="bg-pastel-blue/30 border border-white p-6 rounded-xl shadow-2xs">
                <span className="block text-2xl font-bold text-gray-800">55</span>
                <span className="text-[9px] text-gray-400 uppercase font-semibold">{isThai ? "เสี่ยงถูกต้อง (TP)" : "True Pos (TP)"}</span>
              </div>
            </div>
            <div className="flex justify-center gap-6 text-[10px] text-gray-500 mt-6 border-t border-gray-100 pt-4">
              <span>{isThai ? "ความไวคัดกรอง (Sensitivity):" : "Sensitivity (Recall):"} <strong>84.6%</strong></span>
              <span>{isThai ? "ความจำเพาะ (Specificity):" : "Specificity:"} <strong>89.4%</strong></span>
              <span>{isThai ? "ความแม่นยำทำนายบวก (PPV):" : "PPV (Precision):"} <strong>90.1%</strong></span>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-800">
              {isThai ? "ความเข้าใจตารางผลสัมฤทธิ์" : "Understanding the Matrix"}
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              {isThai ? (
                <>
                  ในการสนับสนุนการคัดกรองความเสี่ยงออทิสติกระยะแรกเริ่ม เป้าหมายหลักคือการลดอัตรา <strong>"หลุดคัดกรอง (False Negatives)"</strong> เพื่อให้มั่นใจว่าจะไม่มีเด็กที่ต้องการความช่วยเหลือหลุดลอดระบบประเมินไป ควบคู่ไปกับการควบคุมจำนวนเคส <strong>"เตือนหลอก (False Positives)"</strong> ให้อยู่ในระดับที่เหมาะสม เพื่อป้องกันภาระงานล้นมือของผู้เชี่ยวชาญการแพทย์
                </>
              ) : (
                <>
                  In early ASD screening support, a key target is minimizing <strong>False Negatives (FN)</strong> (missing children who have ASD risk signals), while also keeping <strong>False Positives (FP)</strong> under control to prevent clinician burnout.
                </>
              )}
            </p>
            <div className="bg-white p-4 rounded-xl border border-gray-100 space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded bg-pastel-blue/40 border border-clinical-blue/20" />
                <span>
                  {isThai 
                    ? <><strong>55 ราย เสี่ยงถูกต้อง</strong>: ตรวจหาพฤติกรรมความเสี่ยงออทิสติกได้ถูกต้องตรงตามประวัติทางคลินิกเพื่อส่งประเมินซ้ำ</>
                    : <><strong>55 True Positives</strong>: Correctly flagged ASD risk patterns for intervention check.</>}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded bg-pastel-pink/30 border border-red-200" />
                <span>
                  {isThai 
                    ? <><strong>10 ราย หลุดคัดกรอง</strong>: เด็กที่มีประวัติเสี่ยงแต่สัญญาณการใช้ภาษาในการพูดคุยกลมกลืนอยู่ในเกณฑ์พัฒนาการปกติ</>
                    : <><strong>10 False Negatives</strong>: Children whose features fell into the typically developing range.</>}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded bg-pastel-blue/40 border border-clinical-blue/20" />
                <span>
                  {isThai 
                    ? <><strong>51 ราย ปกติถูกต้อง</strong>: คัดแยกและประเมินเด็กที่มีสัญญาณการสนทนาตามพัฒนาการปกติได้อย่างตรงพารามิเตอร์</>
                    : <><strong>51 True Negatives</strong>: Correctly identified non-ASD vocal patterns.</>}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* NEW: Cross-Corpus LOCO Table */}
      {activeTab === "loco" && (
        <div className="space-y-6">
          <div className="mb-2">
            <h3 className="text-base font-semibold text-gray-800">
              {isThai ? "ความทนทานแบบข้ามคลังข้อมูล (LOCO)" : "Leave-One-Corpus-Out (LOCO) Robustness"}
            </h3>
            <p className="text-xs text-gray-400">
              {isThai 
                ? "การประเมินความสามารถในการใช้งานทั่วไปของโมเดลโดยกันชุดข้อมูลทั้งกลุ่มออกจากการฝึกสอนในแต่ละรอบ" 
                : "Evaluating classifier generalizability by holding out an entire cohort/corpus during training"}
            </p>
          </div>

          <div className="glass-card rounded-2xl overflow-hidden border border-gray-100">
            <div className="overflow-x-auto">
              <table className="min-w-[960px] divide-y divide-gray-100 text-left text-xs text-gray-500">
                <thead className="bg-gray-50 text-[10px] text-gray-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "คลังข้อมูลที่ถูกกันไว้" : "Held Out Corpus"}</th>
                    <th className="px-6 py-4 whitespace-nowrap">{isThai ? "สถานะประเมิน" : "Status"}</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">{isThai ? "จำนวนประชากร (N)" : "Sample size (N)"}</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">{isThai ? "ความถูกต้อง" : "Accuracy"}</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">{isThai ? "ความไว" : "Sensitivity"}</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">{isThai ? "ความจำเพาะ" : "Specificity"}</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">ROC AUC</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">Brier Score</th>
                    <th className="px-6 py-4 text-right whitespace-nowrap">{isThai ? "อัตราก้ำกึ่ง" : "Uncertain rate"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white font-medium text-gray-700">
                  {loco.map((corpus: any, idx: number) => (
                    <tr key={idx} className={corpus.status === "skipped_single_class" ? "bg-gray-50/50" : ""}>
                      <td className="px-6 py-4 font-bold uppercase whitespace-nowrap">{corpus.held_out_corpus}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold whitespace-nowrap ${
                          corpus.status === "evaluated" ? "bg-pastel-blue text-clinical-blue" : "bg-gray-100 text-gray-400"
                        }`}>
                          {isThai ? (corpus.status === "evaluated" ? "ประเมินผลเสร็จสิ้น" : "ข้ามข้อมูลกลุ่มเดียว") : corpus.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-bold whitespace-nowrap">{corpus.n_test}</td>
                      <td className="px-6 py-4 text-right whitespace-nowrap">{corpus.accuracy ? `${(corpus.accuracy * 100).toFixed(1)}%` : "—"}</td>
                      <td className="px-6 py-4 text-right whitespace-nowrap">{corpus.sensitivity ? `${(corpus.sensitivity * 100).toFixed(1)}%` : "—"}</td>
                      <td className="px-6 py-4 text-right whitespace-nowrap">{corpus.specificity ? `${(corpus.specificity * 100).toFixed(1)}%` : "—"}</td>
                      <td className="px-6 py-4 text-right font-bold whitespace-nowrap">{corpus.roc_auc ? corpus.roc_auc.toFixed(3) : "—"}</td>
                      <td className="px-6 py-4 text-right text-gray-400 whitespace-nowrap">{corpus.brier_score ? corpus.brier_score.toFixed(3) : "—"}</td>
                      <td className="px-6 py-4 text-right text-gray-400 whitespace-nowrap">{corpus.uncertain_rate ? `${(corpus.uncertain_rate * 100).toFixed(1)}%` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-pastel-purple/20 p-4 rounded-xl border border-clinical-purple/10 flex items-start gap-2.5 text-xs text-gray-700">
            <AlertTriangle className="w-4 h-4 mt-0.5 text-clinical-purple shrink-0" />
            <div className="leading-normal">
              <strong>{isThai ? "บทวิเคราะห์ความสามารถทั่วไป (Generalizability):" : "Generalizability Analysis:"}</strong>{" "}
              {isThai ? (
                <>
                  แบบจำลองยังคงรักษาความถูกต้องที่ <strong>70.8%</strong> บนชุดข้อมูลกันออก `eigsti` และ <strong>71.1%</strong> บนชุดข้อมูลกันออก `nadig` แม้ประสิทธิภาพจะลดลงเมื่อเทียบกับการทดสอบทั่วไป (86.9%) แต่สะท้อนความคาดหมายประสิทธิภาพของเอไอจริงในการนำไปใช้ในสภาพแวดล้อมทางคลินิกใหม่ๆ (เช่น การเปลี่ยนโรงพยาบาล หรือ Demographic ของเด็กกลุ่มใหม่) ซึ่งระดับสัญญาณเสียงบันทึกและวิธีการตอบโต้มีเอกลักษณ์เฉพาะตัวต่างกันออกไป
                </>
              ) : (
                <>
                  The model maintains an accuracy of <strong>70.8%</strong> on held-out `eigsti` and <strong>71.1%</strong> on held-out `nadig`. While lower than the stratified cross-validation accuracy (86.9%), this reflects a realistic expectation of model performance when deploying to completely new clinical environments (such as a different hospital cohort or a new demographic group) due to cohort-specific recording styles.
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "subgroups" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Gender Subgroups */}
            <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">
                {isThai ? "ประสิทธิภาพตามเพศสภาพ" : "Performance by Sex"}
              </h3>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={subgroups.filter((s: any) => s.dimension === "sex").map((s: any) => ({
                      ...s,
                      value: isThai ? (s.value === "male" ? "ชาย" : "หญิง") : s.value
                    }))}
                    margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                  >
                    <XAxis dataKey="value" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="accuracy" fill={PASTEL_COLORS.blue} name={isThai ? "ความถูกต้อง" : "Accuracy"} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="sensitivity" fill={PASTEL_COLORS.pink} name={isThai ? "ความไวคัดกรอง" : "Sensitivity"} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Age Subgroups */}
            <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">
                {isThai ? "ประสิทธิภาพตามกลุ่มอายุ" : "Performance by Age Band"}
              </h3>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={subgroups.filter((s: any) => s.dimension === "age_band")}
                    margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                  >
                    <XAxis dataKey="value" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip lang={lang} />} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="accuracy" fill={PASTEL_COLORS.purple} name={isThai ? "ความถูกต้อง" : "Accuracy"} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="sensitivity" fill={PASTEL_COLORS.peach} name={isThai ? "ความไวคัดกรอง" : "Sensitivity"} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50/50 border border-amber-200/50 p-4 rounded-xl flex items-start gap-2.5 text-xs text-amber-800">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <div className="leading-normal">
              <strong>{isThai ? "การตรวจสอบความทนทานในกลุ่มย่อย (Subgroups Audit):" : "Subgroup Robustness Audit:"}</strong>{" "}
              {isThai ? (
                <>
                  เราพบว่าความไวคัดกรอง (Sensitivity) จะมีค่าต่ำลงเล็กน้อยในกลุ่มประชากรย่อยเพศหญิง (57.1% เทียบกับ 78.5% ในเด็กผู้ชาย) และกลุ่มช่วงอายุที่โตขึ้น (เช่น 72+ เดือน) สิ่งนี้มีสาเหตุจากความไม่เท่ากันของจำนวนข้อมูลที่มีอยู่ในกลุ่ม TalkBank/ASDBank ดั้งเดิม นอกจากนี้สัญญาณทางภาษาของเด็กที่อายุมากกว่าจะพัฒนาขึ้นตามธรรมชาติ จึงมีความจำเป็นที่จะต้องขยายข้อมูลเด็กไทยหรือตั้งเกณฑ์คัดกรองจำเพาะกลุ่มวัยขึ้นมาเสริมประสิทธิภาพ
                </>
              ) : (
                <>
                  We notice sensitivity is lower on female subgroups (57.1% vs 78.5% on males) and older age bands (e.g. 72+). This is primarily due to cohort size imbalances in the underlying TalkBank/ASDBank files. In older cohorts, linguistic signals shift, indicating the need for separate age-normative classification baselines.
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// 7. Therapist Workflow Section
// 7. Therapist Workflow Section
export const WorkflowSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const isThai = lang === "TH";
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {isThai ? "ขั้นตอนการทำงานของนักบำบัด" : "Therapist Workflow"}
        </h2>
        <p className="text-sm text-gray-500">
          {isThai 
            ? "การเชื่อมประสานแบบจำลอง AI ร่วมกับผู้เชี่ยวชาญเพื่อความปลอดภัยสูงสุด" 
            : "Human-in-the-Loop integration inside clinical speech assessment"}
        </p>
      </div>

      <div className="relative border-l-2 border-dashed border-pastel-blue pl-6 ml-4 space-y-8 py-2">
        {/* Step 1 */}
        <div className="relative">
          <span className="absolute -left-10 top-0.5 flex items-center justify-center bg-pastel-blue text-clinical-blue font-bold rounded-full w-7 h-7 border border-white text-xs shadow-xs">
            1
          </span>
          <div className="glass-card p-5 rounded-2xl space-y-2">
            <h3 className="font-semibold text-gray-900 text-sm flex items-center gap-1.5">
              {isThai ? "บันทึกเสียงและแยกเสียงสนทนาอัตโนมัติ" : "Audio Recording & Automated Alignment"}
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              {isThai ? (
                <>
                  นักแก้ไขการพูดบันทึกเสียงในเซสชันกิจกรรมการเล่นกับเด็ก 10-20 นาทีอย่างปลอดภัย ไฟล์เสียงจะถูกอัปโหลดเพื่อแยกคนพูด (Diarization) เพื่อแยกแยะประโยคคำพูดของเด็กออกจากประโยคสนทนาของนักบำบัดรักษา
                </>
              ) : (
                <>
                  The speech therapist records a structured play session with the child using toy sets. The audio is uploaded, and processed by speaker diarization to separate child utterances from examiner responses.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Step 2 */}
        <div className="relative">
          <span className="absolute -left-10 top-0.5 flex items-center justify-center bg-pastel-purple text-clinical-purple font-bold rounded-full w-7 h-7 border border-white text-xs shadow-xs">
            2
          </span>
          <div className="glass-card p-5 rounded-2xl space-y-2">
            <h3 className="font-semibold text-gray-900 text-sm flex items-center gap-1.5">
              {isThai ? "ขั้นตอนตรวจสอบคุณภาพโดยมนุษย์ (QA)" : "Human-in-the-Loop Transcript QA"}
            </h3>
            <div className="bg-red-50/50 border border-red-100 p-3 rounded-xl flex items-start gap-2.5 text-[11px] text-red-800 mb-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="leading-normal">
                <strong>{isThai ? "ข้อขอบเขตความปลอดภัย:" : "Safety Boundary:"}</strong>{" "}
                {isThai ? (
                  <>
                    อัลกอริทึมรู้จำเสียงพูดอัตโนมัติ (ASR) มักจะมีความคลาดเคลื่อนในคำพูดเด็กที่ฟังไม่รู้เรื่อง ดังนั้น นักแก้ไขการพูดจำเป็นต้องเข้ามาตรวจสอบประโยคที่ระบบมีความมั่นใจต่ำ และตรวจความเที่ยงตรงของการสลับสรรพนามก่อนสั่งประมวลผลดัชนีชี้วัดเสมอ
                  </>
                ) : (
                  <>
                    Speech-recognition algorithms frequently fail on unintelligible child verbalizations. The clinician must review low-confidence segments and manually check pronoun reversals before running classification.
                  </>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              {isThai ? (
                <>
                  ระบบพอร์ทัลไฮไลต์ประโยคที่ความแม่นยำต่ำเพื่อให้นักบำบัดตรวจสอบความถูกต้อง นักบำบัดสามารถแก้คำผิด ลงรหัสพฤติกรรมเฉพาะ (เช่น การหัวเราะ การเปล่งเสียงไร้ความหมาย หรือการเงียบ) และตรวจสอบความถูกต้องของสัญลักษณ์คนพูด
                </>
              ) : (
                <>
                  The portal highlights parts of the transcript where ASR confidence was low. The clinician adjusts words, codes special vocal markers (like laughter or zero vocalizations), and confirms speaker tags.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Step 3 */}
        <div className="relative">
          <span className="absolute -left-10 top-0.5 flex items-center justify-center bg-pastel-green text-clinical-green font-bold rounded-full w-7 h-7 border border-white text-xs shadow-xs">
            3
          </span>
          <div className="glass-card p-5 rounded-2xl space-y-2">
            <h3 className="font-semibold text-gray-900 text-sm flex items-center gap-1.5">
              {isThai ? "การจำแนกสัญญาณความเสี่ยงและการตรวจสอบเหตุผล" : "Feature Explanation & Screening Risk Inspection"}
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              {isThai ? (
                <>
                  ระบบประมวลผลดัชนีทางภาษาศาสตร์และนำเสนอความน่าจะเป็นของดัชนีชี้วัดความเสี่ยง ทิศทางของฟีเจอร์จะแสดงผลเป็นลูกศรบวก/ลบอย่างโปร่งใส เพื่อให้ผู้ตรวจสอบรู้ว่าเหตุใดโมเดลจึงคำนวณความเสี่ยงออกมาในระดับนั้นๆ
                </>
              ) : (
                <>
                  The system calculates language complexity metrics and presents the screening estimate. Feature contributions are explicitly displayed as positive or negative arrows so the therapist knows *why* the estimate was generated.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Step 4 */}
        <div className="relative">
          <span className="absolute -left-10 top-0.5 flex items-center justify-center bg-pastel-peach text-clinical-peach font-bold rounded-full w-7 h-7 border border-white text-xs shadow-xs">
            4
          </span>
          <div className="glass-card p-5 rounded-2xl space-y-2">
            <h3 className="font-semibold text-gray-900 text-sm flex items-center gap-1.5">
              {isThai ? "การประเมินยืนยันโดยนักบำบัดและการส่งออกรายงาน" : "Clinician Validation & Report Export"}
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed">
              {isThai ? (
                <>
                  นักแก้ไขการพูดประมวลสัญญาณเสี่ยงร่วมกับประเด็นกังวลของผู้ปกครอง (เช่น แบบประเมินความเสี่ยงออทิสติก M-CHAT) และข้อมูลพฤติกรรมเด็กจริง เมื่อผลการประเมินลงตัวแล้ว สามารถพิมพ์รายงานสรุปผลคลินิกในรูปแบบ PDF ได้
                </>
              ) : (
                <>
                  The clinician fuses the AI indicator with parental concern forms (e.g., M-CHAT responses) and physical observations. Once satisfied, they write recommendations and export a PDF clinical report.
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Custom tick renderer for Radar Chart to wrap long labels and prevent overlapping/cut-offs
const CustomRadarTick = (props: any) => {
  const { x, y, payload, cx, cy } = props;
  if (!payload || !payload.value) return null;
  const value = payload.value;

  // Vector from center (cx, cy) to tick (x, y)
  const dx = x - cx;
  const dy = y - cy;

  // Set alignment anchor based on horizontal position relative to center
  let textAnchor: "start" | "middle" | "end" = "middle";
  if (dx > 10) {
    textAnchor = "start";
  } else if (dx < -10) {
    textAnchor = "end";
  }

  // Adjust vertical offset based on position
  let dyOffset = 4;
  if (dy < -20) {
    dyOffset = -6; // pull label up slightly at the top half
  } else if (dy > 20) {
    dyOffset = 12; // push label down slightly at the bottom half
  }

  // Smart splitting of label into lines:
  // E.g., "Grammatical Complexity (MLU)" -> ["Grammatical Complexity", "(MLU)"]
  // E.g., "Speech Intelligibility" -> ["Speech Intelligibility"]
  let lines: string[] = [];
  if (value.includes(" (")) {
    const parts = value.split(" (");
    lines = [parts[0], `(${parts[1]}`];
  } else if (value.length > 20) {
    // split by space closest to the middle
    const words = value.split(" ");
    if (words.length > 1) {
      const mid = Math.ceil(words.length / 2);
      lines = [words.slice(0, mid).join(" "), words.slice(mid).join(" ")];
    } else {
      lines = [value];
    }
  } else {
    lines = [value];
  }

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={0}
        y={dyOffset}
        textAnchor={textAnchor}
        fill="#4B5563"
        fontSize={9}
        fontWeight={500}
        className="font-medium font-sans animate-fade-in"
      >
        {lines.map((line, idx) => (
          <tspan x={0} dy={idx > 0 ? 11 : 0} key={idx}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
};

// Intuitively map feature slider min/max/step values for the simulator
const FEATURE_BOUNDS: Record<string, { min: number; max: number; step: number; suffix?: string }> = {
  age_months: { min: 20, max: 96, step: 1, suffix: "m" },
  total_utterances: { min: 10, max: 800, step: 5 },
  mlu: { min: 0.0, max: 6.0, step: 0.05 },
  mluw: { min: 0.0, max: 6.0, step: 0.05 },
  ttr: { min: 0.05, max: 0.70, step: 0.01 },
  total_words: { min: 20, max: 2000, step: 10 },
  unintelligible_count: { min: 0, max: 150, step: 1 },
  unintelligible_ratio: { min: 0.0, max: 0.8, step: 0.01 },
  zero_vocalization_count: { min: 0, max: 150, step: 1 },
  nonverbal_vocalization_count: { min: 0, max: 100, step: 1 },
  question_ratio: { min: 0.0, max: 0.5, step: 0.01 },
  echolalia_count: { min: 0, max: 50, step: 1 },
  echolalia_ratio: { min: 0.0, max: 0.4, step: 0.01 },
  pronoun_reversal_count: { min: 0, max: 20, step: 1 }
};

// 8. Child Progress Tracking Section
export const ProgressSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const [selectedChild, setSelectedChild] = useState<string>("Roger");
  const progressSummary = projectData.longitudinal_summary;
  const longitudinalDetails = (projectData as any).longitudinal_details || {};

  const currentChildData = progressSummary.find((c: any) => c.child === selectedChild) || progressSummary[0];
  const currentChildTimeline = longitudinalDetails[selectedChild] || [];

  // Prepare simple dataset comparing start vs end metrics for current child
  const chartData = [
    { name: lang === "EN" ? "MLU (morphemes)" : "MLU (หน่วยคำ)", Start: currentChildData.mlu_start, End: currentChildData.mlu_end },
    { name: lang === "EN" ? "Lexical Diversity (TTR)" : "ความหลากหลายคำ (TTR)", Start: currentChildData.ttr_start * 10, End: currentChildData.ttr_end * 10 }, 
    { name: lang === "EN" ? "Unintelligible Ratio" : "สัดส่วนคำที่ไม่ชัดเจน", Start: currentChildData.unintelligible_ratio_start * 10, End: currentChildData.unintelligible_ratio_end * 10 },
  ];

  // Radar chart data for child profile comparison - Expanded to represent all 7 longitudinal parameters
  const radarData = [
    { subject: lang === "EN" ? "Grammatical Complexity (MLU)" : "ความซับซ้อนของไวยากรณ์ (MLU)", Start: Math.min(100, Math.round(currentChildData.mlu_start * 25)), End: Math.min(100, Math.round(currentChildData.mlu_end * 25)) },
    { subject: lang === "EN" ? "Lexical Complexity (MLUw)" : "ความซับซ้อนของคำศัพท์ (MLUw)", Start: Math.min(100, Math.round(currentChildData.mluw_start * 25)), End: Math.min(100, Math.round(currentChildData.mluw_end * 25)) },
    { subject: lang === "EN" ? "Lexical Diversity (TTR)" : "ความหลากหลายของคำศัพท์ (TTR)", Start: Math.min(100, Math.round(currentChildData.ttr_start * 200)), End: Math.min(100, Math.round(currentChildData.ttr_end * 200)) },
    { subject: lang === "EN" ? "Speech Intelligibility" : "ความชัดเจนของคำพูด", Start: Math.round((1 - currentChildData.unintelligible_ratio_start) * 100), End: Math.round((1 - currentChildData.unintelligible_ratio_end) * 100) },
    { subject: lang === "EN" ? "Vocal Response Rate" : "อัตราการตอบสนองทางเสียง", Start: Math.max(0, Math.min(100, 100 - currentChildData.zero_vocalization_count_start)), End: Math.max(0, Math.min(100, 100 - currentChildData.zero_vocalization_count_end)) },
    { subject: lang === "EN" ? "Session Word Volume" : "ปริมาณคำต่อเซสชัน", Start: Math.min(100, Math.round(currentChildData.total_words_start / 15)), End: Math.min(100, Math.round(currentChildData.total_words_end / 15)) },
    { subject: lang === "EN" ? "Conversation Productivity" : "ผลผลิตของการสนทนา", Start: Math.min(100, Math.round(currentChildData.total_utterances_start / 5)), End: Math.min(100, Math.round(currentChildData.total_utterances_end / 5)) }
  ];

  // NEW: Session timeline formatted for Recharts LineChart
  const timelineChartData = currentChildTimeline.map((session: any) => ({
    session_order: lang === "EN" ? `S${session.session_order}` : `ครั้งที่ ${session.session_order}`,
    age_months: session.age_months,
    mlu: session.mlu,
    ttr: session.ttr * 10, // scaled by 10 for visibility on the same scale
    unintelligible_ratio: session.unintelligible_ratio * 10, // scaled by 10
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {lang === "EN" ? "Child Progress Tracking" : "การติดตามพัฒนาการเด็ก"}
        </h2>
        <p className="text-sm text-gray-500">
          {lang === "EN" 
            ? "Longitudinal monitoring of language metrics over multiple sessions" 
            : "การติดตามความคืบหน้าของตัวบ่งชี้ทางภาษาของเด็กเป็นระยะเวลาต่อเนื่องกันหลายครั้ง"}
        </p>
      </div>

      <div className="flex justify-between items-center bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">
          {lang === "EN" ? "Select Child Record:" : "เลือกบันทึกรายชื่อเด็ก:"}
        </span>
        <select
          value={selectedChild}
          onChange={(e) => setSelectedChild(e.target.value)}
          className="bg-gray-50 border border-gray-200 text-xs font-semibold rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-clinical-blue text-gray-700 font-semibold"
        >
          {progressSummary.map((c: any, idx: number) => (
            <option key={idx} value={c.child}>{c.child}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Child Longitudinal Details */}
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
            {lang === "EN" ? "Progress Details" : "รายละเอียดพัฒนาการ"}
          </h3>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
              <span className="text-[10px] text-gray-400 font-semibold block">
                {lang === "EN" ? "SESSIONS" : "จำนวนครั้ง (SESSIONS)"}
              </span>
              <span className="text-lg font-bold text-gray-800">{currentChildData.n_sessions}</span>
            </div>
            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
              <span className="text-[10px] text-gray-400 font-semibold block">
                {lang === "EN" ? "DURATION" : "ระยะเวลา (DURATION)"}
              </span>
              <span className="text-lg font-bold text-gray-800">
                {currentChildData.duration_mo.toFixed(1)} {lang === "EN" ? "m" : "เดือน"}
              </span>
            </div>
            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
              <span className="text-[10px] text-gray-400 font-semibold block">
                {lang === "EN" ? "START AGE" : "อายุเริ่มต้น"}
              </span>
              <span className="text-lg font-bold text-gray-800">
                {(currentChildData.age_start_mo / 12).toFixed(1)} {lang === "EN" ? "yrs" : "ปี"}
              </span>
            </div>
            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
              <span className="text-[10px] text-gray-400 font-semibold block">
                {lang === "EN" ? "END AGE" : "อายุสิ้นสุด"}
              </span>
              <span className="text-lg font-bold text-gray-800">
                {(currentChildData.age_end_mo / 12).toFixed(1)} {lang === "EN" ? "yrs" : "ปี"}
              </span>
            </div>
          </div>

          <div className="bg-pastel-green/30 p-4 rounded-xl border border-clinical-green/10 space-y-1 text-xs">
            <span className="font-semibold text-clinical-green flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" /> {lang === "EN" ? "Developmental Summary" : "สรุปพัฒนาการ"}
            </span>
            <p className="text-gray-600 leading-relaxed pt-1">
              {lang === "EN" ? (
                <>
                  {selectedChild} showed a change in Mean Length of Utterance (MLU) from <strong>{currentChildData.mlu_start.toFixed(2)}</strong> to <strong>{currentChildData.mlu_end.toFixed(2)}</strong> over the study period, illustrating speech-complexity development.
                </>
              ) : (
                <>
                  เด็ก {selectedChild} แสดงการเปลี่ยนแปลงของค่าเฉลี่ยความยาวคำพูด (MLU) จาก <strong>{currentChildData.mlu_start.toFixed(2)}</strong> เป็น <strong>{currentChildData.mlu_end.toFixed(2)}</strong> ในช่วงเวลาที่ติดตามผล ซึ่งแสดงให้เห็นถึงพัฒนาการของความซับซ้อนของคำพูด
                </>
              )}
            </p>
          </div>
        </div>

        {/* Detailed Session-by-Session Line Chart */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between col-span-1 lg:col-span-2">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
                {lang === "EN" ? "Session-by-Session Trends" : "แนวโน้มพัฒนาการแต่ละครั้ง"}
              </h3>
              <p className="text-[10px] text-gray-400">
                {lang === "EN" ? "Tracking child metric progression across all play sessions" : "ติดตามความคืบหน้าของตัวชี้วัดเด็กในแต่ละเซสชันการเล่น"}
              </p>
            </div>
          </div>
          <div className="h-48">
            {timelineChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timelineChartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <XAxis dataKey="session_order" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip content={<CustomTooltip lang={lang} />} />
                  <Legend wrapperStyle={{ fontSize: 9 }} />
                  <Line type="monotone" dataKey="mlu" name={lang === "EN" ? "MLU (morphemes)" : "MLU (หน่วยคำ)"} stroke={CLINICAL_COLORS.blue} strokeWidth={2.5} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="ttr" name={lang === "EN" ? "Lexical Diversity (TTR × 10)" : "ความหลากหลายคำ (TTR × 10)"} stroke={CLINICAL_COLORS.purple} strokeWidth={1.5} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="unintelligible_ratio" name={lang === "EN" ? "Unintelligible Ratio (× 10)" : "สัดส่วนคำที่ไม่ชัดเจน (× 10)"} stroke={PASTEL_COLORS.pink} strokeWidth={1.5} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">
                {lang === "EN" ? `No session timeline available for ${selectedChild}` : `ไม่มีข้อมูลการเล่นของ ${selectedChild}`}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Growth compare */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
            {lang === "EN" ? "Speech Growth Comparison" : "การเปรียบเทียบการเติบโตทางคำพูด"}
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                <YAxis tick={{ fontSize: 9 }} />
                <Tooltip content={<CustomTooltip lang={lang} />} />
                <Legend wrapperStyle={{ fontSize: 9 }} />
                <Bar dataKey="Start" name={lang === "EN" ? "Baseline" : "จุดเริ่มต้น"} fill={PASTEL_COLORS.blue} radius={[4, 4, 0, 0]} />
                <Bar dataKey="End" name={lang === "EN" ? "Outcome" : "จุดสิ้นสุด"} fill={PASTEL_COLORS.green} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Radar profile before/after */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
            {lang === "EN" ? "Developmental Profile (7 Parameters)" : "โพรไฟล์พัฒนาการ (7 พารามิเตอร์)"}
          </h3>
          <div className="h-72 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="58%" data={radarData} margin={{ top: 15, right: 35, bottom: 15, left: 35 }}>
                <PolarGrid stroke="#F3F4F6" />
                <PolarAngleAxis dataKey="subject" tick={<CustomRadarTick />} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 7 }} />
                <Radar name={lang === "EN" ? "Start Profile (Baseline)" : "โปรไฟล์เริ่มต้น (Baseline)"} dataKey="Start" stroke={CLINICAL_COLORS.blue} fill={PASTEL_COLORS.blue} fillOpacity={0.4} />
                <Radar name={lang === "EN" ? "End Profile (Outcome)" : "โปรไฟล์ปลายทาง (Outcome)"} dataKey="End" stroke={CLINICAL_COLORS.green} fill={PASTEL_COLORS.green} fillOpacity={0.4} />
                <Tooltip content={<CustomTooltip lang={lang} />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          {/* HTML-based Legend to prevent overlapping */}
          <div className="flex justify-center gap-4 text-[9px] font-bold mt-2 pt-2 border-t border-gray-50 flex-wrap">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-clinical-blue/40 border border-clinical-blue/20" /> {lang === "EN" ? "Start Profile (Baseline)" : "โปรไฟล์เริ่มต้น (Baseline)"}</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-clinical-green/40 border border-clinical-green/20" /> {lang === "EN" ? "End Profile (Outcome)" : "โปรไฟล์ปลายทาง (Outcome)"}</span>
          </div>
        </div>
      </div>

      {/* Therapy goals checklist */}
      <div className="glass-card p-6 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
          {lang === "EN" ? "Goal Completion Audit (Sample)" : "การตรวจสอบการบรรลุเป้าหมายการบำบัด (ตัวอย่าง)"}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { label: lang === "EN" ? "Grammar Complexity Goal" : "เป้าหมายความซับซ้อนของไวยากรณ์", value: "85%", status: "completed", details: lang === "EN" ? "Target: MLU > 2.5 morphemes" : "เป้าหมาย: MLU > 2.5 หน่วยคำ" },
            { label: lang === "EN" ? "Lexical Diversity Goal" : "เป้าหมายความหลากหลายคำศัพท์", value: "70%", status: "in-progress", details: lang === "EN" ? "Target: TTR > 0.35" : "เป้าหมาย: TTR > 0.35" },
            { label: lang === "EN" ? "Speech Intelligibility" : "เป้าหมายความชัดเจนของเสียงพูด", value: "95%", status: "completed", details: lang === "EN" ? "Target: Unintelligible ratio < 5%" : "เป้าหมาย: สัดส่วนคำไม่ชัดเจน < 5%" },
          ].map((goal, idx) => (
            <div key={idx} className="bg-white p-4 rounded-xl border border-gray-100 flex items-start gap-3 shadow-2xs">
              <span className={`p-1.5 rounded-lg mt-0.5 ${goal.status === "completed" ? "bg-pastel-green/40 text-clinical-green" : "bg-pastel-peach/40 text-clinical-peach"}`}>
                <CheckCircle className="w-4 h-4" />
              </span>
              <div>
                <span className="text-[10px] text-gray-400 font-semibold uppercase">{goal.label}</span>
                <span className="block text-base font-bold text-gray-800">{goal.value}</span>
                <span className="text-[10px] text-gray-500 block mt-0.5">{goal.details}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// 9. Explainability Section
export const ExplainabilitySection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const [activeTab, setActiveTab] = useState<"simulator" | "cohort">("simulator");
  const oofPredictions = projectData.oof_predictions || [];
  const datasetRecords = projectData.dataset_records || [];
  const [loadedChildId, setLoadedChildId] = useState<string | null>(null);

  // Load Logistic Regression Parameters from JSON Database (14 Features)
  const lrParams = (projectData as any).lr_model_parameters || {
    intercept: -3.4776,
    features: {}
  };

  // Dynamically initialize simulator values to feature medians
  const [simulatorValues, setSimulatorValues] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    Object.keys(lrParams.features).forEach((feat) => {
      initial[feat] = lrParams.features[feat].median;
    });
    return initial;
  });

  // Dynamic 14-feature classification risk score calculation
  const calculateRisk = () => {
    let z = lrParams.intercept;
    Object.keys(lrParams.features).forEach((feat) => {
      const val = simulatorValues[feat] ?? lrParams.features[feat].median;
      z += lrParams.features[feat].coef * val;
    });
    const prob = 1 / (1 + Math.exp(-z));
    return Math.round(prob * 100);
  };

  const riskScore = calculateRisk();

  // Determine risk category
  const getRiskCategory = (score: number) => {
    const s = score / 100;
    if (s < projectData.uncertain_thresholds.low) {
      return { 
        label: lang === "EN" ? "Low Risk Signal" : "ระดับความเสี่ยงต่ำ", 
        color: "text-clinical-green bg-pastel-green/40 border-clinical-green/20" 
      };
    } else if (s < projectData.uncertain_thresholds.high) {
      return { 
        label: lang === "EN" ? "Uncertain / Borderline" : "ความเสี่ยงก้ำกึ่ง / ควรเฝ้าระวัง", 
        color: "text-clinical-peach bg-pastel-peach/40 border-clinical-peach/20" 
      };
    } else {
      return { 
        label: lang === "EN" ? "Elevated Risk Signal" : "ระดับความเสี่ยงสูง (แนะนำพบแพทย์)", 
        color: "text-red-600 bg-pastel-pink/40 border-red-200" 
      };
    }
  };

  const riskCat = getRiskCategory(riskScore);

  // Dynamic Linear model SHAP-like contributions: coef * (value - mean)
  const contributionData = Object.keys(lrParams.features)
    .map((feat) => {
      const param = lrParams.features[feat];
      const val = simulatorValues[feat] ?? param.median;
      const mean = param.mean ?? param.median;
      const contrib = param.coef * (val - mean);
      return {
        name: lang === "TH" ? (FEATURE_TRANSLATIONS[feat]?.title || param.title) : param.title,
        value: parseFloat(contrib.toFixed(4)),
        fill: contrib > 0 ? PASTEL_COLORS.pink : PASTEL_COLORS.green
      };
    })
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value)); // sort by importance magnitude

  // Search state for Cohort Explorer
  const [searchOOF, setSearchOOF] = useState("");

  // Filtered out-of-fold prediction list
  const filteredOOF = oofPredictions.filter((p: any) =>
    p.participant_id.toString().includes(searchOOF)
  );

  // Load Child features directly into the 14-feature simulator
  const handleLoadFeatures = (childId: string) => {
    const record = datasetRecords.find((r: any) => r.participant_id.toString() === childId.toString());

    if (record) {
      const newVals: Record<string, number> = {};
      Object.keys(lrParams.features).forEach((feat) => {
        // Find feature value in child record, otherwise default to medians
        let val = (record as any)[feat];
        if (val === undefined || val === null) {
          val = lrParams.features[feat].median;
        }
        newVals[feat] = typeof val === "number" ? parseFloat(val.toFixed(3)) : val;
      });
      setSimulatorValues(newVals);
      setLoadedChildId(childId.toString());
      setActiveTab("simulator"); // switch tabs automatically
    }
  };

  const displayGroup = (g: string) => {
    if (lang === "EN") return g;
    if (g === "ASD") return "กลุ่มเสี่ยง (ASD)";
    if (g === "TD") return "ปกติ (TD)";
    if (g === "DD") return "พัฒนาการล่าช้า (DD)";
    return g;
  };

  const displayUncertainty = (u: string) => {
    if (lang === "EN") return u;
    if (u === "high") return "สูง";
    if (u === "low") return "ต่ำ";
    return "ก้ำกึ่ง (เฝ้าระวัง)";
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {lang === "EN" ? "Explainability (XAI)" : "การอธิบายผลโมเดล (XAI)"}
        </h2>
        <p className="text-sm text-gray-500">
          {lang === "EN" 
            ? "Interactive decision-support risk calculator and cohort out-of-fold predictions explorer" 
            : "เครื่องคำนวณความเสี่ยงเพื่อสนับสนุนการตัดสินใจ และตัวสำรวจการคาดการณ์แบบ Out-of-fold ของกลุ่มตัวอย่าง"}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100">
        <button
          onClick={() => setActiveTab("simulator")}
          className={`px-4 py-2 text-xs font-semibold -mb-px border-b-2 transition-all cursor-pointer ${
            activeTab === "simulator" ? "border-clinical-blue text-clinical-blue" : "border-transparent text-gray-400 hover:text-gray-600"
          }`}
        >
          {lang === "EN" ? "Risk Calculator Simulator" : "เครื่องมือจำลองการคำนวณความเสี่ยง"}
        </button>
        <button
          onClick={() => setActiveTab("cohort")}
          className={`px-4 py-2 text-xs font-semibold -mb-px border-b-2 transition-all cursor-pointer ${
            activeTab === "cohort" ? "border-clinical-blue text-clinical-blue" : "border-transparent text-gray-400 hover:text-gray-600"
          }`}
        >
          {lang === "EN" ? "Cohort Prediction Explorer" : "เครื่องมือสำรวจการคาดการณ์กลุ่มเป้าหมาย"}
        </button>
      </div>

      {activeTab === "simulator" && (
        <div className="space-y-6">
          {loadedChildId && (
            <div className="bg-pastel-blue/30 border border-clinical-blue/20 p-3 rounded-2xl flex justify-between items-center text-xs">
              <span className="text-clinical-blue font-semibold">
                {lang === "EN" ? (
                  <>🔬 Loaded actual features for child ID: <strong>{loadedChildId}</strong></>
                ) : (
                  <>🔬 โหลดฟีเจอร์จริงของเด็กรหัส: <strong>{loadedChildId}</strong></>
                )}
              </span>
              <button
                onClick={() => setLoadedChildId(null)}
                className="text-[10px] bg-white hover:bg-gray-50 px-2 py-1 rounded-lg border border-gray-200 font-bold text-gray-500 cursor-pointer"
              >
                {lang === "EN" ? "Clear" : "ล้างข้อมูล"}
              </button>
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            {/* Simulator Controls - 14 dynamic sliders */}
            <div className="glass-card p-6 rounded-2xl space-y-4 xl:col-span-3">
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-clinical-blue" />
                {lang === "EN" ? "Interactive Feature Simulator (14 Parameters)" : "แบบจำลองพารามิเตอร์แบบโต้ตอบ (14 ฟีเจอร์หลัก)"}
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                {Object.keys(lrParams.features).map((feat) => {
                  const param = lrParams.features[feat];
                  const bounds = FEATURE_BOUNDS[feat] || { min: 0, max: 100, step: 1 };
                  const val = simulatorValues[feat] ?? param.median;
                  const formatValue = (v: number) => {
                    if (bounds.step < 0.1) return v.toFixed(3);
                    if (bounds.step < 1) return v.toFixed(2);
                    return Math.round(v).toString();
                  };
                  const displayedTitle = lang === "TH" ? (FEATURE_TRANSLATIONS[feat]?.title || param.title) : param.title;

                  return (
                    <div key={feat} className="bg-white p-3 rounded-xl border border-gray-100 shadow-2xs space-y-1.5 flex flex-col justify-between">
                      <div className="flex justify-between font-semibold gap-1">
                        <span className="text-gray-700 font-medium truncate" title={displayedTitle}>{displayedTitle}</span>
                        <span className="text-clinical-blue font-bold whitespace-nowrap">
                          {formatValue(val)}{bounds.suffix || ""}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={bounds.min}
                        max={bounds.max}
                        step={bounds.step}
                        value={val}
                        onChange={(e) => {
                          setSimulatorValues({
                            ...simulatorValues,
                            [feat]: Number(e.target.value)
                          });
                        }}
                        className="w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-clinical-blue"
                      />
                      <div className="flex justify-between text-[8px] text-gray-400 font-medium pt-0.5">
                        <span>Min: {bounds.min}</span>
                        <span>Median: {formatValue(param.median)}</span>
                        <span>Max: {bounds.max}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Risk Output Display */}
            <div className="glass-card p-6 rounded-2xl flex flex-col justify-between text-center border border-gray-100 xl:col-span-1">
              <div>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
                  {lang === "EN" ? "Risk Estimate" : "การประเมินสัญญาณความเสี่ยง"}
                </h3>
                <span className="text-[10px] text-gray-400 font-medium block">
                  {lang === "EN" ? "Logistic Regression Probability" : "ความน่าจะเป็นโดยโมเดล Logistic Regression"}
                </span>
              </div>

              <div className="my-6">
                <span className="text-5xl font-extrabold text-gray-800 font-display block">{riskScore}%</span>
                <span className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide mt-3 border ${riskCat.color}`}>
                  {riskCat.label}
                </span>
              </div>

              <div className="text-[10px] text-gray-500 leading-normal border-t border-gray-50 pt-3">
                {lang === "EN" ? (
                  <>Threshold values: <strong>&lt;40%</strong> Low Risk; <strong>40-60%</strong> Borderline/Uncertain; <strong>&gt;60%</strong> Elevated Risk.</>
                ) : (
                  <>เกณฑ์การพิจารณา: <strong>&lt;40%</strong> สัญญาณต่ำ; <strong>40-60%</strong> สัญญาณก้ำกึ่ง; <strong>&gt;60%</strong> สัญญาณสูง (ควรส่งต่อแพทย์)</>
                )}
              </div>
            </div>
          </div>

          {/* Contribution bar chart */}
          <div className="glass-card p-6 rounded-2xl">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">
              {lang === "EN" ? "Linear Model Feature Contributions (ASD Risk Impact)" : "น้ำหนักของแต่ละพารามิเตอร์ต่อการตัดสินใจของโมเดล (ผลกระทบต่อความเสี่ยง ASD)"}
            </h3>
            <div className="h-[460px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={contributionData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <XAxis type="number" tick={{ fontSize: 9 }} />
                  <YAxis dataKey="name" type="category" tick={<CustomYAxisTick />} width={200} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip lang={lang} />} />
                  <Bar dataKey="value" name={lang === "EN" ? "Contribution" : "น้ำหนักส่งผล"} radius={[0, 4, 4, 0]}>
                    {contributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex gap-4 justify-center text-[10px] text-gray-500 mt-2 border-t border-gray-50 pt-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-pastel-pink" /> 
                {lang === "EN" ? "Positive weight (increases risk estimate)" : "น้ำหนักทางบวก (เพิ่มระดับความเสี่ยง)"}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-pastel-green" /> 
                {lang === "EN" ? "Negative weight (reduces risk estimate)" : "น้ำหนักทางลบ (ลดระดับความเสี่ยง)"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* NEW: Cohort out-of-fold predictions explorer */}
      {activeTab === "cohort" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center flex-wrap gap-4 border-b border-gray-50 pb-4">
            <div>
              <h3 className="text-base font-semibold text-gray-800">
                {lang === "EN" ? "Out-of-Fold (OOF) Prediction Records" : "บันทึกผลการทำนายแบบ Out-of-Fold (OOF)"}
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                {lang === "EN" 
                  ? "Double-blind validation outputs showing probability distributions for all children" 
                  : "ผลการทดสอบการคาดการณ์แบบปิดสองทางข้ามกลุ่ม (Double-Blind Validation) สำหรับเด็กทุกคนในชุดข้อมูล"}
              </p>
            </div>

            <div className="relative text-xs">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
                <Search className="w-3.5 h-3.5" />
              </span>
              <input
                type="text"
                placeholder={lang === "EN" ? "Search child ID..." : "ค้นหารหัสเด็ก..."}
                value={searchOOF}
                onChange={(e) => setSearchOOF(e.target.value)}
                className="pl-9 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-clinical-blue text-gray-700 font-semibold"
              />
            </div>
          </div>

          <div className="overflow-hidden border border-gray-100 rounded-2xl">
            <div className="max-h-96 overflow-y-auto overflow-x-auto custom-scrollbar">
              <table className="min-w-[1024px] divide-y divide-gray-100 text-left text-xs text-gray-500">
                <thead className="bg-gray-50 text-[10px] text-gray-400 font-bold uppercase tracking-wider sticky top-0 z-10">
                  <tr>
                    <th className="px-6 py-3 bg-gray-50 whitespace-nowrap">{lang === "EN" ? "Child ID" : "รหัสเด็ก"}</th>
                    <th className="px-6 py-3 bg-gray-50 whitespace-nowrap">{lang === "EN" ? "Corpus" : "คลังข้อมูล"}</th>
                    <th className="px-6 py-3 bg-gray-50 text-center whitespace-nowrap">{lang === "EN" ? "True Group" : "กลุ่มจริง (ตรวจประเมินโดยแพทย์)"}</th>
                    <th className="px-6 py-3 bg-gray-50 text-right whitespace-nowrap">{lang === "EN" ? "Classifier Probability" : "ความน่าจะเป็นจากแบบจำลอง"}</th>
                    <th className="px-6 py-3 bg-gray-50 text-center whitespace-nowrap">{lang === "EN" ? "Risk Estimate" : "ระดับความเสี่ยงที่ทำนาย"}</th>
                    <th className="px-6 py-3 bg-gray-50 text-center whitespace-nowrap">{lang === "EN" ? "Uncertainty Zone" : "ระดับความผันผวน"}</th>
                    <th className="px-6 py-3 bg-gray-50 text-center whitespace-nowrap">{lang === "EN" ? "Actions" : "ดำเนินการ"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white font-medium text-gray-700">
                  {filteredOOF.length > 0 ? (
                    filteredOOF.map((pred: any, idx: number) => {
                      const probPercent = Math.round(pred.prob_asd * 100);

                      return (
                        <tr key={idx} className="hover:bg-gray-50/50">
                          <td className="px-6 py-3 font-bold text-gray-900 whitespace-nowrap">{pred.participant_id}</td>
                          <td className="px-6 py-3 uppercase text-[10px] text-gray-400 whitespace-nowrap">{pred.corpus}</td>
                          <td className="px-6 py-3 text-center whitespace-nowrap">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold whitespace-nowrap ${
                              pred.group === "ASD" ? "bg-pastel-blue text-clinical-blue" : "bg-gray-100 text-gray-500"
                            }`}>
                              {displayGroup(pred.group)}
                            </span>
                          </td>
                          <td className="px-6 py-3 text-right font-extrabold text-gray-800 whitespace-nowrap">{probPercent}%</td>
                          <td className="px-6 py-3 text-center whitespace-nowrap">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold whitespace-nowrap ${
                              pred.pred_050 === 1 ? "text-red-600 bg-pastel-pink/40" : "text-clinical-green bg-pastel-green/40"
                            }`}>
                              {pred.pred_050 === 1 
                                ? (lang === "EN" ? "At Risk" : "มีระดับความเสี่ยง") 
                                : (lang === "EN" ? "Low Risk" : "ระดับความเสี่ยงต่ำ")
                              }
                            </span>
                          </td>
                          <td className="px-6 py-3 text-center whitespace-nowrap">
                            <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border whitespace-nowrap ${
                              pred.uncertainty_zone === "high" ? "text-red-500 bg-red-50 border-red-100" :
                              pred.uncertainty_zone === "low" ? "text-clinical-green bg-green-50 border-green-100" :
                              "text-clinical-peach bg-amber-50 border-amber-100"
                            }`}>
                              {displayUncertainty(pred.uncertainty_zone)}
                            </span>
                          </td>
                          <td className="px-6 py-3 text-center whitespace-nowrap">
                            <button
                              onClick={() => handleLoadFeatures(pred.participant_id)}
                              className="text-[10px] bg-pastel-blue text-clinical-blue hover:bg-pastel-blue-dark px-2.5 py-1 rounded-lg border border-clinical-blue/20 font-bold transition-colors cursor-pointer whitespace-nowrap"
                            >
                              {lang === "EN" ? "🔬 Load Features" : "🔬 โหลดฟีเจอร์"}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                        {lang === "EN" ? "No prediction records matching search." : "ไม่พบข้อมูลที่ตรงกับการค้นหา"}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <div className="text-[10px] text-gray-400 text-right font-medium">
            {lang === "EN" 
              ? `Showing ${filteredOOF.length} of ${oofPredictions.length} prediction audits` 
              : `แสดง ${filteredOOF.length} จากทั้งหมด ${oofPredictions.length} รายการตรวจวิเคราะห์`
            }
          </div>
        </div>
      )}
    </div>
  );
};

// 10. Ethics, Safety, and Limitations Section
export const SafetySection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {lang === "EN" ? "Ethics, Safety & Limitations" : "จริยธรรม ความปลอดภัย และข้อจำกัด"}
        </h2>
        <p className="text-sm text-gray-500">
          {lang === "EN" ? "Essential clinical boundaries and governance rules" : "ขอบเขตทางคลินิกที่สำคัญและกฎเกณฑ์การกำกับดูแล"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Constraints */}
        <div className="glass-card p-6 rounded-2xl space-y-4 border-l-4 border-l-red-400">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-pastel-pink text-red-500"><AlertTriangle className="w-4 h-4" /></span>
            {lang === "EN" ? "Model Boundaries & Safe Wording" : "ขอบเขตของโมเดลและการเลือกใช้ถ้อยคำที่ปลอดภัย"}
          </h3>
          <ul className="space-y-3.5 text-sm text-gray-600">
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-2 shrink-0" />
              <span>
                {lang === "EN" ? (
                  <><strong>Screening-Support Boundary:</strong> The classifier output represents a screening support estimate only. Qualified physicians and clinical teams must make any clinical determination using standardized clinical tools and professional judgment.</>
                ) : (
                  <><strong>ไม่มีการวินิจฉัยโรค:</strong> ผลลัพธ์ของโมเดลแสดงถึงตัวชี้วัดเพื่อ 'สนับสนุนการคัดกรอง' เท่านั้น เฉพาะแพทย์ผู้เชี่ยวชาญที่ใช้เครื่องมือประเมินมาตรฐาน (เช่น ADOS-2, CARS-2) เท่านั้นที่สามารถวินิจฉัยสภาวะออทิสติกได้</>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-2 shrink-0" />
              <span>
                {lang === "EN" ? (
                  <><strong>Corpus Limitations:</strong> Model training features are from English-speaking ASDBank files. **No Thai Validation** has been conducted yet; applying this classifier to Thai child speech will introduce feature drift.</>
                ) : (
                  <><strong>ข้อจำกัดของชุดข้อมูล:</strong> แบบจำลองถูกฝึกฝนด้วยข้อมูลภาษาอังกฤษจากคลังข้อมูล ASDBank **ยังไม่มีการทดสอบทางคลินิกในเด็กไทย** การนำแบบจำลองนี้ไปประเมินคำพูดภาษาไทยโดยตรงอาจทำให้ค่าทางภาษาเกิดความเบี่ยงเบน (Feature Drift)</>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-2 shrink-0" />
              <span>
                {lang === "EN" ? (
                  <><strong>Pronoun Reversal Caveat:</strong> The pronoun reversal feature is a simple lookup pattern in English; translation mapping or dialects require manual clinician verification.</>
                ) : (
                  <><strong>ข้อควรระวังการสลับสรรพนาม:</strong> การทำงานของการสลับสรรพนามเป็นเพียงตัวตรวจจับรูปแบบคำศัพท์พื้นฐาน การตีความในทางภาษาจำเป็นต้องอาศัยนักบำบัดร่วมตรวจสอบความสอดคล้องตามบริบท</>
                )}
              </span>
            </li>
          </ul>
        </div>

        {/* Mitigations */}
        <div className="glass-card p-6 rounded-2xl space-y-4 border-l-4 border-l-clinical-green">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-pastel-green text-clinical-green"><ShieldCheck className="w-4 h-4" /></span>
            {lang === "EN" ? "Governance & Mitigation Strategies" : "การกำกับดูแลและกลยุทธ์การลดความเสี่ยง"}
          </h3>
          <ul className="space-y-3.5 text-sm text-gray-600">
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-clinical-green mt-2 shrink-0" />
              <span>
                {lang === "EN" ? (
                  <><strong>Human-in-the-Loop:</strong> The system enforces a mandatory transcript check step where the therapist reviews word segmentations before running classifications.</>
                ) : (
                  <><strong>ผู้เชี่ยวชาญควบคุมระบบ:</strong> ระบบกำหนดให้มีขั้นตอนตรวจสอบบทถอดเสียงสนทนาโดยนักบำบัดรักษาก่อนส่งคำนวณความเสี่ยง เพื่อป้องกันข้อผิดพลาดจากการแปลงเสียงเป็นข้อความ</>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-clinical-green mt-2 shrink-0" />
              <span>
                {lang === "EN" ? (
                  <><strong>Explicit Uncertainty Zone:</strong> Estimates with probabilities between 40% and 60% are flagged as "Uncertain/Borderline" instead of forced classification, prompting therapist audit.</>
                ) : (
                  <><strong>ระบุโซนความก้ำกึ่งชัดเจน:</strong> กรณีที่ระดับความน่าจะเป็นตกอยู่ในช่วง 40% ถึง 60% ระบบจะติดป้ายเตือน 'พื้นที่ก้ำกึ่ง (Uncertain)' แทนการจัดกลุ่มแบบขาวดำ เพื่อให้นักบำบัดประเมินเชิงลึกเพิ่มเติม</>
                )}
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <div className="w-1.5 h-1.5 rounded-full bg-clinical-green mt-2 shrink-0" />
              <span>
                {lang === "EN" ? (
                  <><strong>Data Privacy:</strong> No raw audio coordinates or PII (names, specific locations) are saved globally or uploaded. All processing is transient and reports are local.</>
                ) : (
                  <><strong>การปกป้องความเป็นส่วนตัว:</strong> ไม่มีการบันทึกเสียงดิบหรือข้อมูลส่วนบุคคลที่ระบุตัวตนได้ลงในฐานข้อมูลส่วนกลาง การประมวลผลและการจัดทำรายงานทั้งหมดดำเนินการในเครื่องของระบบเท่านั้น</>
                )}
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

// 11. Roadmap Section
export const RoadmapSection: React.FC<{ lang?: "EN" | "TH" }> = ({ lang = "TH" }) => {
  const [viewMode, setViewMode] = useState<"milestones" | "drift">("milestones");
  const [selectedWer, setSelectedWer] = useState<10 | 25 | 40>(25);

  const milestones = [
    { 
      title: lang === "EN" ? "Thai Language Validation Trials" : "การทดสอบการใช้งานภาษาไทยเชิงคลินิก", 
      date: "Q3 2026", 
      desc: lang === "EN" 
        ? "Collaborating with local hospitals to validate the feature set on Thai-speaking child cohorts, adjusting for morphological differences." 
        : "ร่วมมือกับโรงพยาบาลในประเทศเพื่อทดสอบความถูกต้องของชุดฟีเจอร์ในกลุ่มเด็กไทย โดยปรับแก้ให้เข้ากับความแตกต่างทางสัณฐานวิทยาของภาษา", 
      status: "upcoming", 
      color: "border-t-pastel-blue" 
    },
    { 
      title: lang === "EN" ? "Acoustic Feature Fusion" : "การผสานฟีเจอร์ทางอคูสติกของเสียง", 
      date: "Q4 2026", 
      desc: lang === "EN" 
        ? "Integrating acoustic profile indicators (voiced ratio, pitch variance, pause rates) into the classifier alongside text features." 
        : "ผสานตัวบ่งชี้โพรไฟล์เสียงพูด (อัตราการเปล่งเสียง ความแปรปรวนของระดับเสียง และอัตราการหยุดเว้นวรรค) เข้ากับฟีเจอร์ข้อความ", 
      status: "upcoming", 
      color: "border-t-pastel-purple" 
    },
    { 
      title: lang === "EN" ? "Multimodal Fusion (M-CHAT-R)" : "การผสานหลายรูปแบบร่วมกับ M-CHAT-R", 
      date: "Q1 2027", 
      desc: lang === "EN" 
        ? "Fusing transcript features with standard parent checklist scores (M-CHAT-R/F) to generate a unified risk profile." 
        : "รวมฟีเจอร์จากการสนทนาเข้ากับคะแนนแบบประเมินผู้ปกครองมาตรฐาน (M-CHAT-R/F) เพื่อสร้างผลการประเมินความเสี่ยงที่เป็นหนึ่งเดียว", 
      status: "upcoming", 
      color: "border-t-pastel-peach" 
    },
    { 
      title: lang === "EN" ? "Mobile Speech Collection Portal" : "พอร์ทัลเก็บรวบรวมเสียงพูดบนมือถือ", 
      date: "Q2 2027", 
      desc: lang === "EN" 
        ? "Developing a tablet/mobile application for easy home/school play session recording and instant clinician routing." 
        : "พัฒนาแอปพลิเคชันบนแท็บเล็ต/มือถือเพื่อให้ง่ายต่อการบันทึกเสียงในห้องเรียนหรือที่บ้าน พร้อมส่งต่อไปยังนักบำบัดรักษาทันที", 
      status: "upcoming", 
      color: "border-t-pastel-green" 
    },
  ];

  // Retrieve current stats according to selected WER level
  const currentSummary = thaiDriftData.drift_summary.find((s: any) => s.wer_value === selectedWer) || {
    mlu_mae: 0.24, mlu_bias: -0.24, ttr_mae: 0.045, ttr_bias: 0.045, echolalia_mae: 0.02, echolalia_bias: -0.015,
    label_en: "25% WER", label_th: "25% WER"
  };

  // Build scatter plot values
  const scatterData = thaiDriftData.scatter_data.map((item: any) => {
    const werKey = `wer_${selectedWer}` as 'wer_10' | 'wer_25' | 'wer_40';
    const asrData = item[werKey] || { asr_mlu: 0.0, asr_ttr: 0.0, asr_echolalia: 0.0 };
    return {
      case_id: item.case_id,
      group: item.group,
      age_months: item.age_months,
      gold_mlu: item.gold_mlu,
      gold_ttr: item.gold_ttr,
      gold_echolalia: item.gold_echolalia,
      asr_mlu: asrData.asr_mlu,
      asr_ttr: asrData.asr_ttr,
      asr_echolalia: asrData.asr_echolalia
    };
  });

  const tdScatter = scatterData.filter((d: any) => d.group === "TD");
  const asdScatter = scatterData.filter((d: any) => d.group === "ASD");
  const ddScatter = scatterData.filter((d: any) => d.group === "DD");

  const barChartData = thaiDriftData.drift_summary.map((s: any) => ({
    name: `${s.wer_value}% WER`,
    "MLU MAE": s.mlu_mae,
    "TTR MAE": s.ttr_mae,
  }));

  // Simple diagonal line points (Y = X) to draw in ScatterChart
  const lineOfEquality = [
    { x: 0, y: 0 },
    { x: 5, y: 5 }
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="border-b border-gray-100 pb-4">
        <h2 className="text-2xl font-display font-semibold text-gray-900">
          {lang === "EN" ? "Project Roadmap" : "แผนดำเนินงานโครงการ"}
        </h2>
        <p className="text-sm text-gray-500">
          {lang === "EN" ? "Planned milestones and future developmental directions" : "เป้าหมายที่วางแผนไว้และทิศทางการพัฒนาในอนาคต"}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100">
        <button
          onClick={() => setViewMode("milestones")}
          className={`px-4 py-2 border-b-2 font-semibold text-xs transition-all cursor-pointer ${
            viewMode === "milestones" 
              ? "border-clinical-blue text-clinical-blue font-bold" 
              : "border-transparent text-gray-400 hover:text-gray-600"
          }`}
        >
          🌐 {lang === "EN" ? "Roadmap Milestones" : "แผนงานโครงการ"}
        </button>
        <button
          onClick={() => setViewMode("drift")}
          className={`px-4 py-2 border-b-2 font-semibold text-xs transition-all cursor-pointer ${
            viewMode === "drift" 
              ? "border-clinical-blue text-clinical-blue font-bold" 
              : "border-transparent text-gray-400 hover:text-gray-600"
          }`}
        >
          📊 {lang === "EN" ? "Thai Validation & ASR Drift Simulator" : "จำลองความคลาดเคลื่อน ASR ภาษาไทย"}
        </button>
      </div>

      {viewMode === "milestones" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {milestones.map((ms, idx) => (
            <div key={idx} className={`glass-card p-6 rounded-2xl border-t-4 ${ms.color} flex flex-col justify-between h-48`}>
              <div>
                <div className="flex justify-between items-start">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{ms.date}</span>
                  <span className="text-[9px] font-semibold text-clinical-blue px-2 py-0.5 rounded-full bg-pastel-blue border border-clinical-blue/20">
                    {lang === "EN" ? "Planned" : "วางแผนไว้"}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 text-sm mt-3">{ms.title}</h3>
                <p className="text-xs text-gray-500 mt-2 leading-relaxed">{ms.desc}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
            <div>
              <h4 className="font-semibold text-gray-900 text-xs">
                {lang === "EN" ? "Audio Fidelity & WER Configurations" : "ระดับคุณภาพเสียงพูดและค่าความผิดพลาด WER"}
              </h4>
              <p className="text-[10px] text-gray-400">
                {lang === "EN" ? "Simulating transcription degradation over 40 child cases" : "จำลองการบิดเบือนของข้อมูลในเด็กไทย 40 รายเพื่อประเมินความคลาดเคลื่อน"}
              </p>
            </div>
            <div className="flex gap-2">
              {[10, 25, 40].map((werVal) => (
                <button
                  key={werVal}
                  onClick={() => setSelectedWer(werVal as any)}
                  className={`px-3 py-1.5 rounded-xl font-bold text-[10px] cursor-pointer transition-all ${
                    selectedWer === werVal
                      ? "bg-clinical-blue text-white shadow-xs"
                      : "bg-gray-100 hover:bg-gray-200 text-gray-600"
                  }`}
                >
                  {werVal}% WER {werVal === 10 ? "(Low Noise)" : werVal === 25 ? "(Mid Noise)" : "(High Noise)"}
                </button>
              ))}
            </div>
          </div>

          {/* KPI Dashboard */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                {lang === "EN" ? "Simulation Scenario" : "สภาพแวดล้อมจำลอง"}
              </span>
              <div className="font-bold text-gray-900 text-xs mt-1 truncate">
                {lang === "EN" ? currentSummary.label_en : currentSummary.label_th}
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                {lang === "EN" ? "MLU Mean Absolute Error" : "ความคลาดเคลื่อนเฉลี่ย MLU"}
              </span>
              <div className="font-display font-bold text-clinical-blue text-xl mt-1">
                {currentSummary.mlu_mae.toFixed(3)}
              </div>
              <div className="text-[9px] text-gray-400 mt-0.5">
                Bias: <span className="font-semibold text-amber-600">{currentSummary.mlu_bias > 0 ? "+" : ""}{currentSummary.mlu_bias.toFixed(3)}</span>
              </div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                {lang === "EN" ? "TTR Mean Absolute Error" : "ความคลาดเคลื่อนเฉลี่ย TTR"}
              </span>
              <div className="font-display font-bold text-clinical-purple text-xl mt-1">
                {currentSummary.ttr_mae.toFixed(3)}
              </div>
              <div className="text-[9px] text-gray-400 mt-0.5">
                Bias: <span className="font-semibold text-emerald-600">{currentSummary.ttr_bias > 0 ? "+" : ""}{currentSummary.ttr_bias.toFixed(3)}</span>
              </div>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-2xs">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                {lang === "EN" ? "Echolalia Drift MAE" : "ความเพี้ยนเฉลี่ย Echolalia"}
              </span>
              <div className="font-display font-bold text-clinical-peach text-xl mt-1">
                {currentSummary.echolalia_mae.toFixed(4)}
              </div>
              <div className="text-[9px] text-gray-400 mt-0.5">
                Bias: <span className="font-semibold text-amber-600">{currentSummary.echolalia_bias > 0 ? "+" : ""}{currentSummary.echolalia_bias.toFixed(4)}</span>
              </div>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Scatter Plot */}
            <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-2xs space-y-4">
              <div>
                <h4 className="font-semibold text-gray-900 text-xs">
                  {lang === "EN" ? "ASR vs Gold Transcript MLU Scatter" : "การกระจายตัวของ MLU (ASR เทียบกับ Gold Transcript)"}
                </h4>
                <p className="text-[10px] text-gray-400">
                  {lang === "EN" 
                    ? "Points falling below the diagonal line show negative bias (underestimated sentence length)." 
                    : "จุดที่อยู่ใต้เส้นเอียงเฉียงบ่งชี้อคติเชิงลบ (ความยาวประโยคเด็กถูกประเมินต่ำกว่าจริง)"}
                </p>
              </div>
              
              <div className="h-64 text-[10px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                    <XAxis 
                      type="number" 
                      dataKey="gold_mlu" 
                      name="Gold MLU" 
                      domain={[0.5, 5.0]} 
                      label={{ value: "Gold MLU (ความจริง)", position: "insideBottom", offset: -10 }} 
                    />
                    <YAxis 
                      type="number" 
                      dataKey="asr_mlu" 
                      name="ASR MLU" 
                      domain={[0.5, 5.0]} 
                      label={{ value: "ASR MLU (แกะจากเสียง)", angle: -90, position: "insideLeft", offset: 0 }} 
                    />
                    <ZAxis type="number" range={[50, 50]} />
                    <Tooltip 
                      cursor={{ strokeDasharray: "3 3" }} 
                      formatter={(value: any, name: any) => [value, name]}
                    />
                    <Legend verticalAlign="top" height={36} />
                    
                    {/* Perfect Match Diagonal Line */}
                    <Scatter 
                      name={lang === "EN" ? "Perfect Match (No Drift)" : "ข้อมูลตรงกันสมบูรณ์"} 
                      data={lineOfEquality} 
                      line={{ stroke: "#9CA3AF", strokeWidth: 1, strokeDasharray: "5 5" }} 
                      shape={() => null}
                      legendType="line"
                    />
                    
                    {/* Series by group */}
                    <Scatter 
                      name="TD Cohort" 
                      data={tdScatter} 
                      fill="#A0C4FF" 
                      shape="circle" 
                    />
                    <Scatter 
                      name="ASD Cohort" 
                      data={asdScatter} 
                      fill="#FFADAD" 
                      shape="triangle" 
                    />
                    <Scatter 
                      name="DD Cohort" 
                      data={ddScatter} 
                      fill="#FFD6A5" 
                      shape="wye" 
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Drift Trend Chart */}
            <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-2xs space-y-4">
              <div>
                <h4 className="font-semibold text-gray-900 text-xs">
                  {lang === "EN" ? "Mean Absolute Error by WER Tier" : "ค่าความคลาดเคลื่อนสะสมเฉลี่ยตามระดับเสียงรบกวน"}
                </h4>
                <p className="text-[10px] text-gray-400">
                  {lang === "EN" 
                    ? "Shows how feature drift increases as ASR transcription quality degrades." 
                    : "แสดงแนวโน้มความคลาดเคลื่อนที่เพิ่มขึ้นเมื่อคุณภาพการถอดเสียงลดต่ำลง (WER สูงขึ้น)"}
                </p>
              </div>

              <div className="h-64 text-[10px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barChartData} margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
                    <XAxis dataKey="name" />
                    <YAxis label={{ value: "Mean Absolute Error (MAE)", angle: -90, position: "insideLeft", offset: 0 }} />
                    <Tooltip />
                    <Legend verticalAlign="top" height={36} />
                    <Bar dataKey="MLU MAE" fill="#A0C4FF" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="TTR MAE" fill="#BDB2FF" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Thai ASR Error Distribution Analysis */}
          <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-2xs space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-sm">
                {lang === "EN" ? "Clinical Error Profile of Thai ASR Features" : "รายละเอียดความคลาดเคลื่อนทางภาษาศาสตร์ในการถอดเสียงเด็กไทย"}
              </h3>
              <p className="text-[10px] text-gray-400">
                {lang === "EN" 
                  ? "Analysis of linguistical errors specific to Thai ASR engines and their diagnostic impact." 
                  : "ผลการจำแนกประเภทข้อบกพร่องทางภาษาพูดเฉพาะในภาษาไทยของระบบ ASR และผลกระทบต่อฟีเจอร์สำหรับรายงานวิจัย"}
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-[11px] text-left text-gray-600 border-collapse">
                <thead>
                  <tr className="border-b border-gray-100 text-gray-400 uppercase text-[9px] font-bold">
                    <th className="py-2.5 px-3 w-1/4">{lang === "EN" ? "Error Pattern" : "รูปแบบข้อผิดพลาด"}</th>
                    <th className="py-2.5 px-3 w-12 text-center">{lang === "EN" ? "Freq" : "ความถี่"}</th>
                    <th className="py-2.5 px-3">{lang === "EN" ? "Clinical Feature Impact" : "ผลกระทบต่อฟีเจอร์ทางภาษา"}</th>
                    <th className="py-2.5 px-3">{lang === "EN" ? "Mitigation Strategy" : "แนวทางจัดการในระบบ"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {thaiDriftData.error_distribution.map((err: any, idx: number) => (
                    <tr key={idx} className="hover:bg-gray-50/50">
                      <td className="py-3 px-3 font-semibold text-gray-800">{err.error_type}</td>
                      <td className="py-3 px-3 text-center font-bold text-gray-500">{err.frequency}</td>
                      <td className="py-3 px-3 text-xs leading-relaxed text-gray-600">{err.effect}</td>
                      <td className="py-3 px-3 text-xs leading-relaxed text-clinical-blue font-medium">{err.solution}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Clinical Governance & Warning Card */}
          <div className="bg-amber-50/60 p-6 rounded-2xl border border-amber-100/70 space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
              <h4 className="font-bold text-amber-900 text-xs">
                {lang === "EN" ? "Clinical Safety Statement for Thai Cohorts" : "ข้อชี้แจงความปลอดภัยทางคลินิกสำหรับคลังข้อมูลภาษาไทย"}
              </h4>
            </div>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              {lang === "EN" 
                ? "This dashboard demonstrates that ASR degradation introduces systematic bias to linguistic features: MLU is systematically underestimated, and TTR is artificially inflated. Speech therapists must always manually review and correct transcripts before clinical case evaluation. Automated decisions based on raw ASR features without human oversight are strictly prohibited." 
                : "ชุดจำลองการเบี่ยงเบนของข้อมูลนี้แสดงให้เห็นว่า การลดลงของความถูกต้องของระบบถอดเสียง (ASR) จะส่งผลเชิงระบบ (Systematic Bias) ต่อฟีเจอร์ทางภาษาพูดของเด็กไทย: ความยาวประโยคเฉลี่ย (MLU) จะถูกประเมินต่ำกว่าจริง และสถิติคำศัพท์ (TTR) จะสูงขึ้นผิดปกติ นักบำบัดภาษาพูดจึงต้องตรวจทานทรานสคริปต์ด้วยตนเองเสมอ ห้ามนำเอาค่าจากโมเดล ASR ไปวิเคราะห์ความเสี่ยงโดยไม่มีการมีส่วนร่วมของมนุษย์ (Human-in-the-loop) ในกระบวนการบำบัดรักษาจริง"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
