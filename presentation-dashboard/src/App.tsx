import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Database,
  Layers,
  Map,
  ShieldCheck,
  TrendingUp,
  UserCheck,
  Users,
  Zap,
} from "lucide-react";
import {
  HeroSection,
  ProblemSection,
  ArchitectureSection,
  DatasetSection,
  FeatureSection,
  PerformanceSection,
  WorkflowSection,
  ProgressSection,
  ExplainabilitySection,
  SafetySection,
  RoadmapSection,
} from "./components/DashboardSections";

// Bilingual section labels
const SECTION_LABELS: Record<string, { EN: string; TH: string }> = {
  hero: { EN: "Hero Overview", TH: "ภาพรวมโครงการ" },
  problem: { EN: "Problem & Clinical Context", TH: "ปัญหาและบริบททางคลินิก" },
  architecture: { EN: "System Architecture", TH: "สถาปัตยกรรมระบบ" },
  dataset: { EN: "Dataset Overview", TH: "ภาพรวมชุดข้อมูล" },
  features: { EN: "Feature Dashboard", TH: "แดชบอร์ดฟีเจอร์" },
  performance: { EN: "Model Performance", TH: "ประสิทธิภาพโมเดล" },
  workflow: { EN: "Therapist Workflow", TH: "ขั้นตอนการทำงานของนักบำบัด" },
  progress: { EN: "Child Progress Tracking", TH: "การติดตามพัฒนาการเด็ก" },
  explainability: { EN: "Explainability (XAI)", TH: "การอธิบายผลโมเดล (XAI)" },
  safety: { EN: "Ethics & Safety", TH: "จริยธรรมและความปลอดภัย" },
  roadmap: { EN: "Project Roadmap", TH: "แผนดำเนินงานโครงการ" },
};

const SECTIONS = [
  { id: "hero", icon: Activity, component: HeroSection },
  { id: "problem", icon: AlertTriangle, component: ProblemSection },
  { id: "architecture", icon: Layers, component: ArchitectureSection },
  { id: "dataset", icon: Database, component: DatasetSection },
  { id: "features", icon: BookOpen, component: FeatureSection },
  { id: "performance", icon: TrendingUp, component: PerformanceSection },
  { id: "workflow", icon: UserCheck, component: WorkflowSection },
  { id: "progress", icon: Users, component: ProgressSection },
  { id: "explainability", icon: Zap, component: ExplainabilitySection },
  { id: "safety", icon: ShieldCheck, component: SafetySection },
  { id: "roadmap", icon: Map, component: RoadmapSection },
];

function App() {
  const [activeSectionId, setActiveSectionId] = useState<string>("hero");
  const [lang, setLang] = useState<"EN" | "TH">("TH"); // Default to Thai

  const currentIdx = SECTIONS.findIndex((s) => s.id === activeSectionId);
  const ActiveComponent = SECTIONS[currentIdx].component;

  const handleNext = () => {
    if (currentIdx < SECTIONS.length - 1) {
      setActiveSectionId(SECTIONS[currentIdx + 1].id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handlePrev = () => {
    if (currentIdx > 0) {
      setActiveSectionId(SECTIONS[currentIdx - 1].id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-gray-50/50">
      
      {/* Sidebar navigation */}
      <aside className="w-full md:w-64 bg-white border-r border-gray-100 flex flex-col justify-between md:sticky md:top-0 md:h-screen shrink-0 shadow-2xs z-20">
        <div>
          {/* Logo / Header */}
          <div className="p-6 border-b border-gray-50 flex items-center gap-3">
            <span className="h-7 w-7 rounded-xl bg-gradient-to-tr from-clinical-blue to-clinical-purple flex items-center justify-center text-white font-bold text-sm shadow-sm shrink-0">
              α
            </span>
            <div className="flex justify-between items-center w-full min-w-0">
              <div className="truncate">
                <h2 className="font-display font-bold text-gray-900 text-sm leading-none truncate">asd-project</h2>
              </div>
              {/* Language Selector */}
              <button
                onClick={() => setLang(lang === "EN" ? "TH" : "EN")}
                className="bg-gray-50 hover:bg-pastel-blue border border-gray-200/80 hover:border-clinical-blue/20 text-[10px] font-bold px-2 py-1 rounded-lg text-gray-700 hover:text-clinical-blue transition-all shrink-0 cursor-pointer flex items-center gap-0.5 ml-2"
                title={lang === "EN" ? "Switch to Thai" : "สลับเป็นภาษาอังกฤษ"}
              >
                🌐 {lang === "EN" ? "TH" : "EN"}
              </button>
            </div>
          </div>

          {/* Menu Items */}
          <nav className="p-4 space-y-1">
            {SECTIONS.map((section) => {
              const Icon = section.icon;
              const isActive = section.id === activeSectionId;
              const label = SECTION_LABELS[section.id][lang];
              return (
                <button
                  key={section.id}
                  onClick={() => {
                    setActiveSectionId(section.id);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left text-xs font-semibold transition-all ${
                    isActive
                      ? "bg-pastel-blue text-clinical-blue font-bold border border-clinical-blue/10"
                      : "text-gray-500 hover:bg-gray-50 hover:text-gray-800"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-clinical-blue" : "text-gray-400"}`} />
                  {label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-gray-50 bg-gray-50/30 text-[10px] text-gray-400 leading-normal">
          {lang === "EN" 
            ? "Developed for advisors, speech-language therapists, and non-technical stakeholders." 
            : "พัฒนาขึ้นสำหรับอาจารย์ที่ปรึกษา นักแก้ไขการพูด และผู้เกี่ยวข้องภายนอกคลินิก"}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-screen overflow-x-hidden">
        
        {/* Safety Disclaimer Banner */}
        <header className="bg-amber-50 border-b border-amber-100 px-6 py-3 flex items-start sm:items-center gap-2.5 text-xs text-amber-800 shadow-2xs relative z-10">
          <AlertTriangle className="w-4.5 h-4.5 text-amber-600 mt-0.5 sm:mt-0 shrink-0" />
          <p className="leading-relaxed">
            <strong>{lang === "EN" ? "Clinical Safety Disclaimer:" : "คำชี้แจงความปลอดภัยทางคลินิก:"}</strong>{" "}
            {lang === "EN" 
              ? "This system is for screening support and clinical decision support only. It does not replace assessment by qualified professionals."
              : "ระบบนี้เป็นระบบช่วยสนับสนุนการคัดกรองและการตัดสินใจทางคลินิกเท่านั้น ไม่สามารถใช้ทดแทนการประเมินโดยตรงจากผู้เชี่ยวชาญทางการแพทย์ได้"}
          </p>
        </header>

        {/* Content Viewport */}
        <div className="flex-1 p-6 md:p-8 max-w-5xl w-full mx-auto space-y-8">
          <ActiveComponent lang={lang} />
          
          {/* Slide Navigation Controller */}
          <div className="flex justify-between items-center pt-8 border-t border-gray-100 text-xs">
            <button
              onClick={handlePrev}
              disabled={currentIdx === 0}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl font-semibold border border-gray-200 transition-all ${
                currentIdx === 0
                  ? "opacity-40 cursor-not-allowed bg-gray-50 text-gray-400"
                  : "bg-white text-gray-600 hover:bg-gray-50 active:scale-98"
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
              {lang === "EN" ? "Previous Section" : "ส่วนก่อนหน้า"}
            </button>

            <span className="text-gray-400 font-medium">
              {lang === "EN" 
                ? `Section ${currentIdx + 1} of ${SECTIONS.length}` 
                : `หน้า ${currentIdx + 1} จากทั้งหมด ${SECTIONS.length}`}
            </span>

            <button
              onClick={handleNext}
              disabled={currentIdx === SECTIONS.length - 1}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl font-semibold border border-gray-200 transition-all ${
                currentIdx === SECTIONS.length - 1
                  ? "opacity-40 cursor-not-allowed bg-gray-50 text-gray-400"
                  : "bg-white text-gray-600 hover:bg-gray-50 active:scale-98"
              }`}
            >
              {lang === "EN" ? "Next Section" : "ส่วนถัดไป"}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-100 py-6 px-8 text-center text-[10px] text-gray-400 mt-auto">
          &copy; {new Date().getFullYear()} asd-Project Team. {lang === "EN" ? "Designed with clinical precision and pastel aesthetics." : "ออกแบบด้วยความเที่ยงตรงทางคลินิกและสุนทรียศาสตร์พาสเทล"}
        </footer>
      </main>
    </div>
  );
}

export default App;
