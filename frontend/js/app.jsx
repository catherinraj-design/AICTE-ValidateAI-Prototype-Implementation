const { useState, useEffect, useMemo } = React;

const API_BASE = window.location.origin.includes(":8000") ? "" : "http://localhost:8000";

// Supported 8 Indian Languages
const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी (Hindi)" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "te", label: "తెలుగు (Telugu)" },
  { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
  { code: "ml", label: "മലയാളം (Malayalam)" },
  { code: "mr", label: "मराठी (Marathi)" },
  { code: "bn", label: "বাংলা (Bengali)" }
];

function App() {
  const [currentLang, setCurrentLang] = useState(() => {
    return localStorage.getItem("aicte_validate_ai_lang") || "en";
  });
  const [translations, setTranslations] = useState({});
  const [currentRole, setCurrentRole] = useState("SCRUTINY_OFFICER");
  const [activeTab, setActiveTab] = useState("SCRUTINY_DESK");
  const [applications, setApplications] = useState([]);
  const [selectedApp, setSelectedApp] = useState(null);
  const [selectedDocIndex, setSelectedDocIndex] = useState(0);
  const [showElaHeatmap, setShowElaHeatmap] = useState(false);
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [metrics, setMetrics] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditChainStatus, setAuditChainStatus] = useState(null);
  const [rules, setRules] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // Real-time SSE Pipeline Progress State
  const [realtimeTask, setRealtimeTask] = useState(null);
  const [realtimeStage, setRealtimeStage] = useState(null);

  // Decision Modal State
  const [decisionType, setDecisionType] = useState("APPROVED");
  const [decisionRemarks, setDecisionRemarks] = useState("");
  const [showDecisionModal, setShowDecisionModal] = useState(false);

  // Rectification Modal State
  const [rectifyDoc, setRectifyDoc] = useState(null);
  const [rectifyExplanation, setRectifyExplanation] = useState("");
  const [rectifyFileName, setRectifyFileName] = useState("");
  const [showRectifyModal, setShowRectifyModal] = useState(false);

  // Load translations for active language
  useEffect(() => {
    fetch(`/src/locales/${currentLang}.json`)
      .then((r) => r.json())
      .then((data) => setTranslations(data))
      .catch((e) => {
        console.warn(`Failed to load ${currentLang}.json, falling back to en.json`, e);
        fetch(`/src/locales/en.json`)
          .then((r) => r.json())
          .then((data) => setTranslations(data));
      });
    localStorage.setItem("aicte_validate_ai_lang", currentLang);
  }, [currentLang]);

  // Translation helper function
  const t = (path, fallback = "") => {
    const keys = path.split(".");
    let curr = translations;
    for (const k of keys) {
      if (!curr || typeof curr !== "object") return fallback || path;
      curr = curr[k];
    }
    return curr !== undefined ? curr : fallback || path;
  };

  // Interpolated message code helper
  const tMsg = (code, params = {}) => {
    let template = t(`messages.${code}`, code);
    for (const [key, val] of Object.entries(params)) {
      template = template.replace(new RegExp(`{{${key}}}`, "g"), val);
    }
    return template;
  };

  // Load applications
  const fetchApplications = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/applications`);
      if (res.ok) {
        const data = await res.json();
        setApplications(data);
        if (data.length > 0 && !selectedApp) {
          fetchApplicationDetails(data[0].id);
        }
      }
    } catch (e) {
      console.error("Error fetching applications:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchApplicationDetails = async (appId) => {
    try {
      const res = await fetch(`${API_BASE}/api/applications/${appId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedApp(data);
        setSelectedDocIndex(0);
        setShowElaHeatmap(false);
      }
    } catch (e) {
      console.error("Error fetching details:", e);
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/metrics`);
      if (res.ok) setMetrics(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/audit-trail`);
      if (res.ok) setAuditLogs(await res.json());
      const vRes = await fetch(`${API_BASE}/api/audit-trail/verify`);
      if (vRes.ok) setAuditChainStatus(await vRes.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchRules = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/rules`);
      if (res.ok) setRules(await res.json());
      const sRes = await fetch(`${API_BASE}/api/settings`);
      if (sRes.ok) setSettings(await sRes.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchApplications();
    fetchMetrics();
    fetchAuditLogs();
    fetchRules();
  }, []);

  const showToast = (msg, type = "success") => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Submit Officer Decision
  const handleOfficerDecisionSubmit = async () => {
    if (!decisionRemarks || decisionRemarks.trim().length < 5) {
      showToast("Statutory Safeguard: Officer justification remarks (min 5 chars) are mandatory.", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/applications/${selectedApp.application.id}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: decisionType,
          remarks: decisionRemarks,
          officer_id: "USR-OFFICER-01",
          officer_name: "Dr. R. K. Seshadri (Scrutiny Officer)"
        })
      });
      if (res.ok) {
        showToast(`Regulatory Decision recorded successfully: ${decisionType}`, "success");
        setShowDecisionModal(false);
        setDecisionRemarks("");
        fetchApplications();
        fetchApplicationDetails(selectedApp.application.id);
        fetchAuditLogs();
        fetchMetrics();
      } else {
        const err = await res.json();
        showToast(err.detail || "Decision failed", "error");
      }
    } catch (e) {
      showToast("Network error submitting decision", "error");
    }
  };

  // Submit Rectification
  const handleRectificationSubmit = async () => {
    if (!rectifyExplanation) {
      showToast("Please provide rectification explanation", "error");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/applications/${selectedApp.application.id}/rectify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: rectifyDoc.id,
          explanation: rectifyExplanation,
          file_name: rectifyFileName || "Rectified_Certificate_2026.pdf"
        })
      });
      if (res.ok) {
        showToast("Rectified document submitted. Queued for officer re-scrutiny.", "success");
        setShowRectifyModal(false);
        setRectifyExplanation("");
        fetchApplications();
        fetchApplicationDetails(selectedApp.application.id);
        fetchAuditLogs();
        fetchMetrics();
      }
    } catch (e) {
      showToast("Error submitting rectification", "error");
    }
  };

  // Filtered applications list
  const filteredApps = applications.filter((app) => {
    const matchesFilter =
      filterStatus === "ALL" ||
      (filterStatus === "CRITICAL" && app.risk_level === "CRITICAL") ||
      (filterStatus === "HIGH" && (app.risk_level === "HIGH" || app.risk_level === "CRITICAL")) ||
      (filterStatus === "EXPIRED" && app.overall_status === "EXPIRED") ||
      (filterStatus === "MISMATCH" && app.overall_status === "MISMATCH_DETECTED") ||
      (filterStatus === "CLEAN" && (app.overall_status === "CLEAN" || app.overall_status === "APPROVED"));

    const matchesSearch =
      !searchQuery ||
      app.institution_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.application_no?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.permanent_id?.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  const curDoc = selectedApp?.application?.documents?.[selectedDocIndex] || null;

  return (
    <div className="min-h-screen flex flex-col bg-slate-100">
      {/* Indian Tricolor Stripe */}
      <div className="tricolor-bar"></div>

      {/* Official Government Header */}
      <header className="bg-slate-900 text-white shadow-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-amber-500/20 border border-amber-400 flex items-center justify-center font-bold text-amber-400 text-xl shadow-inner">
              🏛️
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider text-amber-400 font-semibold">
                {t("org_title", "All India Council for Technical Education")} | {t("govt_title", "Government of India")}
              </div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                {t("app_title", "AICTE ValidateAI")}
                <span className="text-xs font-normal px-2 py-0.5 rounded bg-blue-900 text-blue-200 border border-blue-700">
                  {t("subtitle", "AI-Assisted Decision-Support Platform")}
                </span>
              </h1>
            </div>
          </div>

          {/* Multilingual Chooser & Role Switcher */}
          <div className="flex items-center gap-3">
            {/* Language Chooser Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1">
              <span className="text-sm">🌐</span>
              <select
                value={currentLang}
                onChange={(e) => setCurrentLang(e.target.value)}
                className="bg-transparent text-xs text-amber-300 font-medium focus:outline-none cursor-pointer"
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code} className="bg-slate-900 text-white">
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Role Switcher */}
            <select
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              className="bg-slate-800 text-xs text-slate-200 border border-slate-700 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="SCRUTINY_OFFICER">{t("nav.role_officer", "Scrutiny Officer")}</option>
              <option value="INSTITUTION">{t("nav.role_institution", "Institution Applicant")}</option>
              <option value="AUTHORITY">{t("nav.role_admin", "AICTE Bureau Director")}</option>
            </select>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex overflow-x-auto border-t border-slate-800/80">
          {[
            { id: "SCRUTINY_DESK", label: t("nav.scrutiny_desk", "📋 Scrutiny Desk Queue") },
            { id: "DOSSIER_INSPECTOR", label: t("nav.dossier_inspector", "🔬 Dossier & Forensic Inspector") },
            { id: "INSTITUTION_PORTAL", label: t("nav.institution_portal", "🏛️ Institution Portal") },
            { id: "INFRA_GEOFENCE", label: t("nav.infra_geofence", "🛰️ Infrastructure & Geofence") },
            { id: "RULES_ADMIN", label: t("nav.rules_admin", "⚖️ APH Norms & Config") },
            { id: "EVALUATION_METRICS", label: t("nav.evaluation_metrics", "📊 Live Evaluation Metrics") },
            { id: "AUDIT_TRAIL", label: t("nav.audit_trail", "🔒 Cryptographic Audit Chain") }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-xs font-semibold whitespace-nowrap transition-colors border-b-2 flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? "border-amber-400 text-amber-400 bg-slate-800/60"
                  : "border-transparent text-slate-300 hover:text-white hover:bg-slate-800/30"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Advisory Guardrail Banner */}
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-1.5 text-xs text-amber-900 flex items-center justify-center gap-2 text-center font-medium">
        <span className="font-bold uppercase tracking-wider text-amber-800 bg-amber-200/80 px-1.5 py-0.5 rounded text-[10px]">
          {t("statutory_safeguard_title", "Statutory Safeguard")}
        </span>
        {t("statutory_safeguard_banner")}
      </div>

      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg shadow-xl text-sm font-medium flex items-center gap-2 border transition-all ${
            notification.type === "error"
              ? "bg-red-50 text-red-900 border-red-300"
              : "bg-emerald-50 text-emerald-900 border-emerald-300"
          }`}
        >
          <span>{notification.type === "error" ? "⚠️" : "✅"}</span>
          <span>{notification.msg}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* ========================================================================= */}
        {/* TAB 1: SCRUTINY DESK QUEUE */}
        {/* ========================================================================= */}
        {activeTab === "SCRUTINY_DESK" && (
          <div className="space-y-6">
            {/* Top KPI Metrics Bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs text-slate-500 font-medium">{t("desk.total_applications")}</div>
                <div className="text-2xl font-bold text-slate-800 mt-1">{applications.length}</div>
                <div className="text-xs text-blue-600 mt-1">15 Synthetic Seed Institutions</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs text-slate-500 font-medium">{t("desk.critical_risks")}</div>
                <div className="text-2xl font-bold text-red-600 mt-1">
                  {applications.filter((a) => a.risk_level === "CRITICAL" || a.risk_level === "HIGH").length}
                </div>
                <div className="text-xs text-red-500 mt-1">Planted defects detected</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs text-slate-500 font-medium">{t("desk.authority_mismatches")}</div>
                <div className="text-2xl font-bold text-amber-600 mt-1">
                  {applications.filter((a) => a.overall_status === "MISMATCH_DETECTED" || a.overall_status === "EXPIRED").length}
                </div>
                <div className="text-xs text-amber-600 mt-1">Fire NOC / Bhulekh Land / QR</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="text-xs text-slate-500 font-medium">{t("desk.clean_baselines")}</div>
                <div className="text-2xl font-bold text-emerald-600 mt-1">
                  {applications.filter((a) => a.overall_status === "CLEAN" || a.overall_status === "APPROVED").length}
                </div>
                <div className="text-xs text-emerald-600 mt-1">Ready for expedited EoA grant</div>
              </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2">
                {[
                  { id: "ALL", label: t("desk.all_filter") },
                  { id: "CRITICAL", label: t("desk.critical_filter") },
                  { id: "MISMATCH", label: t("desk.mismatch_filter") },
                  { id: "EXPIRED", label: t("desk.expired_filter") },
                  { id: "CLEAN", label: t("desk.clean_filter") }
                ].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setFilterStatus(f.id)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      filterStatus === f.id
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <div className="w-full sm:w-72">
                <input
                  type="text"
                  placeholder={t("common.search_placeholder")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
            </div>

            {/* Applications Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider border-b border-slate-200 font-semibold">
                    <tr>
                      <th className="px-4 py-3">{t("common.pid")}</th>
                      <th className="px-4 py-3">{t("common.institution")}</th>
                      <th className="px-4 py-3">State & Category</th>
                      <th className="px-4 py-3">Application Type</th>
                      <th className="px-4 py-3">{t("common.risk")}</th>
                      <th className="px-4 py-3">{t("common.status")}</th>
                      <th className="px-4 py-3 text-right">{t("common.actions")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {filteredApps.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 font-mono text-slate-700 font-semibold">
                          {app.permanent_id}
                          <div className="text-[10px] text-slate-400 font-normal">{app.application_no}</div>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-900 max-w-xs truncate">
                          {app.institution_name}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {app.state}
                          <div className="text-[10px] text-slate-400">{app.district}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {app.category?.replace(/_/g, " ")}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              app.risk_level === "CRITICAL"
                                ? "badge-critical"
                                : app.risk_level === "HIGH"
                                ? "badge-high"
                                : app.risk_level === "MEDIUM"
                                ? "badge-medium"
                                : "badge-clean"
                            }`}
                          >
                            {app.risk_level} ({app.overall_risk_score}/100)
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                              app.overall_status === "CLEAN" || app.overall_status === "APPROVED"
                                ? "bg-emerald-100 text-emerald-800"
                                : app.overall_status === "MISMATCH_DETECTED"
                                ? "bg-red-100 text-red-800"
                                : app.overall_status === "EXPIRED"
                                ? "bg-orange-100 text-orange-800"
                                : app.overall_status === "EVC_INSPECTION_RECOMMENDED"
                                ? "bg-purple-100 text-purple-800"
                                : "bg-slate-200 text-slate-800"
                            }`}
                          >
                            {app.overall_status?.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => {
                              fetchApplicationDetails(app.id);
                              setActiveTab("DOSSIER_INSPECTOR");
                            }}
                            className="bg-blue-800 hover:bg-blue-900 text-white font-medium px-3 py-1.5 rounded-lg text-xs transition-colors shadow-sm"
                          >
                            {t("common.inspect")}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: DOSSIER & FORENSIC DOCUMENT INSPECTOR */}
        {/* ========================================================================= */}
        {activeTab === "DOSSIER_INSPECTOR" && selectedApp && (
          <div className="space-y-6">
            {/* Institution Dossier Header */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">
                    PID: {selectedApp.application?.institution?.permanent_id}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    App No: {selectedApp.application?.application_no}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-slate-900 mt-1">
                  {selectedApp.application?.institution?.name}
                </h2>
                <div className="text-xs text-slate-600 mt-0.5 flex flex-wrap gap-x-4">
                  <span>📍 {selectedApp.application?.institution?.district}, {selectedApp.application?.institution?.state}</span>
                  <span>🎓 {selectedApp.application?.institution?.affiliating_university}</span>
                  <span>📐 {t("common.acres")}: {selectedApp.application?.institution?.registered_land_acres}</span>
                </div>
              </div>

              {/* Status and Officer Action Button */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-right">
                  <div className="text-xs text-slate-500">{t("dossier.overall_risk")}</div>
                  <div className="text-xl font-bold flex items-center gap-1 justify-end">
                    <span
                      className={
                        selectedApp.application?.overall_risk_score > 60
                          ? "text-red-600"
                          : selectedApp.application?.overall_risk_score > 30
                          ? "text-amber-600"
                          : "text-emerald-600"
                      }
                    >
                      {selectedApp.application?.overall_risk_score} / 100
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setShowDecisionModal(true)}
                  className="bg-amber-600 hover:bg-amber-700 text-white font-semibold px-4 py-2 rounded-lg text-xs shadow-md transition-all flex items-center gap-1.5"
                >
                  {t("dossier.officer_panel_btn")}
                </button>
              </div>
            </div>

            {/* Checklist Completion Banner */}
            {selectedApp.checklist_evaluation && (
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-slate-800">{t("dossier.checklist_progress")}:</span>
                  <div className="w-48 bg-slate-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full ${
                        selectedApp.checklist_evaluation.completion_percentage === 100
                          ? "bg-emerald-500"
                          : "bg-amber-500"
                      }`}
                      style={{ width: `${selectedApp.checklist_evaluation.completion_percentage}%` }}
                    ></div>
                  </div>
                  <span className="font-mono font-bold text-slate-700">
                    {selectedApp.checklist_evaluation.completion_percentage}%
                  </span>
                </div>
                <div className="text-slate-600">
                  Required: {selectedApp.checklist_evaluation.total_mandatory_required} | Missing:{" "}
                  <span className="text-red-600 font-bold">
                    {selectedApp.checklist_evaluation.missing_mandatory_count}
                  </span>{" "}
                  | Deficient:{" "}
                  <span className="text-amber-600 font-bold">
                    {selectedApp.checklist_evaluation.deficient_count}
                  </span>
                </div>
              </div>
            )}

            {/* Dual-Pane Document Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* LEFT PANE: Document Selector & Interactive Viewer (lg:col-span-7) */}
              <div className="lg:col-span-7 space-y-4">
                {/* Document Tab Selector */}
                <div className="bg-white p-2 rounded-xl border border-slate-200 shadow-sm flex overflow-x-auto gap-2">
                  {(selectedApp.application?.documents || []).map((doc, idx) => (
                    <button
                      key={doc.id}
                      onClick={() => {
                        setSelectedDocIndex(idx);
                        setShowElaHeatmap(false);
                      }}
                      className={`px-3 py-1.5 text-xs rounded-lg font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                        selectedDocIndex === idx
                          ? "bg-blue-900 text-white shadow-sm"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`}
                    >
                      <span>
                        {doc.doc_type === "FIRE_SAFETY_NOC"
                          ? "🔥"
                          : doc.doc_type === "LAND_OWNERSHIP_DEED"
                          ? "📜"
                          : doc.doc_type === "AFFILIATING_UNIV_NOC"
                          ? "🎓"
                          : "📄"}
                      </span>
                      <span>{doc.title}</span>
                      {doc.risk_level === "CRITICAL" && (
                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Interactive Document Viewer Canvas */}
                {curDoc ? (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
                    <div className="bg-slate-900 text-white px-4 py-2.5 flex items-center justify-between text-xs">
                      <div className="font-medium flex items-center gap-2">
                        <span>📄 {curDoc.file_name}</span>
                        <span className="text-slate-400">({curDoc.file_size_kb} KB)</span>
                      </div>

                      {/* ELA Heatmap Toggle Button */}
                      <button
                        onClick={() => setShowElaHeatmap(!showElaHeatmap)}
                        className={`px-3 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-colors ${
                          showElaHeatmap
                            ? "bg-red-600 text-white ring-2 ring-red-400"
                            : "bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700"
                        }`}
                      >
                        <span>{showElaHeatmap ? "🔴" : "🔍"}</span>
                        <span>{showElaHeatmap ? t("dossier.hide_ela") : t("dossier.view_ela")}</span>
                      </button>
                    </div>

                    {/* Document Simulation Display */}
                    <div className="relative p-6 bg-slate-50 min-h-[460px] flex items-center justify-center border-b border-slate-200">
                      <div className="w-full max-w-lg bg-white border border-slate-300 rounded shadow-lg p-6 relative font-serif text-slate-800 text-xs">
                        <div className="text-center border-b pb-3 mb-3">
                          <div className="font-bold text-sm tracking-wide text-slate-900 uppercase">
                            GOVERNMENT OF NCT OF DELHI / STATE DIRECTORATE
                          </div>
                          <div className="text-[11px] text-slate-600 font-sans">
                            COMPETENT STATUTORY AUTHORITY REGISTERED CERTIFICATE
                          </div>
                        </div>

                        <div className="space-y-3 font-sans text-xs">
                          <div className="flex justify-between items-center text-slate-500 text-[11px]">
                            <div>PID: <span className="font-bold text-slate-800">{curDoc.extracted_fields?.find(f => f.field_name === "permanent_id")?.value || selectedApp.application?.institution?.permanent_id}</span></div>
                            <div>Date: <span className="font-bold text-slate-800">{curDoc.extracted_fields?.find(f => f.field_name === "issue_date")?.value || "12/08/2025"}</span></div>
                          </div>

                          <div className="p-2 bg-slate-50 rounded border border-slate-200">
                            <span className="text-[11px] text-slate-500 block">Certificate Registration / Order No:</span>
                            <span className="font-mono font-bold text-blue-900 text-xs">
                              {curDoc.extracted_fields?.find(f => f.field_name === "reference_no")?.value || "NOC-REG-2026-X"}
                            </span>
                          </div>

                          <p className="leading-relaxed text-slate-700">
                            This is to certify that premises of institution <strong>{curDoc.extracted_fields?.find(f => f.field_name === "institution_name")?.value || selectedApp.application?.institution?.name}</strong> have been formally inspected and confirmed compliant under statutory provisions.
                          </p>

                          <div className="p-3 bg-amber-50/60 rounded border border-amber-200 flex justify-between items-center">
                            <div>
                              <span className="text-[11px] text-amber-800 font-bold block">Validity Expiration Date:</span>
                              <span className={`text-sm font-bold font-mono ${curDoc.is_expired ? "text-red-600" : "text-emerald-700"}`}>
                                {curDoc.valid_upto || "31/07/2027"}
                              </span>
                            </div>
                            {curDoc.is_expired && (
                              <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 text-[10px] font-bold border border-red-300">
                                {t("common.expired")}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Interactive Bounding Box Renderings */}
                        {curDoc.extracted_fields?.map((f, i) => (
                          f.bbox && (
                            <div
                              key={i}
                              title={`${f.label}: ${f.value} (${Math.round(f.confidence * 100)}% conf)`}
                              style={{
                                position: "absolute",
                                top: `${f.bbox.ymin * 100}%`,
                                left: `${f.bbox.xmin * 100}%`,
                                width: `${(f.bbox.xmax - f.bbox.xmin) * 100}%`,
                                height: `${(f.bbox.ymax - f.bbox.ymin) * 100}%`
                              }}
                              className="border-2 border-dashed border-blue-500 bg-blue-500/10 hover:bg-blue-500/20 rounded pointer-events-auto transition-all cursor-pointer flex items-start justify-end p-0.5"
                            >
                              <span className="bg-blue-600 text-white text-[9px] px-1 rounded font-sans font-bold leading-none">
                                {f.label.split(" ")[0]}
                              </span>
                            </div>
                          )
                        ))}

                        {/* ELA Heatmap Overlay Layer */}
                        {showElaHeatmap && (
                          <div className="absolute inset-0 bg-slate-900/80 rounded flex flex-col items-center justify-center p-4 text-center z-10 transition-all backdrop-blur-[1px]">
                            <div className="text-red-400 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-1">
                              <span>⚠️</span> Error Level Analysis (ELA) Tampering Heatmap
                            </div>
                            <div className="relative border-2 border-red-500 rounded p-4 bg-black/60 max-w-xs text-left text-xs font-mono">
                              <div className="text-emerald-400 text-[11px] mb-1">Compression Disparity: High</div>
                              <div className="text-slate-300 text-[10px] leading-tight">
                                High error pixels concentrated around validity date string '30/06/2027'. Localized tamper patch detected.
                              </div>
                              <div className="mt-2 w-full h-16 bg-gradient-to-r from-blue-900 via-orange-600 to-red-600 rounded border border-red-400/50 flex items-center justify-center text-white text-[10px] font-bold shadow-inner">
                                [Localized Tamper Splice Region]
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Document Meta Footer */}
                    <div className="p-3 bg-slate-50 text-xs text-slate-500 flex flex-wrap items-center justify-between gap-2">
                      <span>Status: <strong className="text-slate-800">{curDoc.overall_status}</strong></span>
                      <span>Risk Score: <strong className={curDoc.risk_score > 50 ? "text-red-600" : "text-emerald-600"}>{curDoc.risk_score} / 100</strong></span>
                    </div>
                  </div>
                ) : (
                  <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500 text-xs">
                    Select a document to inspect entities and forensic overlays.
                  </div>
                )}
              </div>

              {/* RIGHT PANE: Extracted Entities, Forensic Findings, Issuing Authority Check (lg:col-span-5) */}
              <div className="lg:col-span-5 space-y-4">
                {/* 1. OCR Extracted Regulatory Entities Table */}
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <span>📑</span> {t("dossier.extracted_entities")}
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-600 text-[11px]">
                        <tr>
                          <th className="py-1.5 px-2 font-medium">{t("dossier.field")}</th>
                          <th className="py-1.5 px-2 font-medium">{t("dossier.value")}</th>
                          <th className="py-1.5 px-2 font-medium text-right">{t("dossier.confidence")}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {(curDoc?.extracted_fields || []).map((f, i) => (
                          <tr key={i} className="hover:bg-slate-50">
                            <td className="py-2 px-2 text-slate-500 font-medium">{f.label}</td>
                            <td className="py-2 px-2 font-semibold text-slate-900 font-mono text-[11px]">{f.value}</td>
                            <td className="py-2 px-2 text-right">
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold">
                                {Math.round(f.confidence * 100)}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 2. Anomaly & Forensic Findings Card */}
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>🔬</span> {t("dossier.anomalies_title")}
                  </h3>

                  {(curDoc?.forensic_findings || []).length > 0 ? (
                    <div className="space-y-3">
                      {curDoc.forensic_findings.map((f, i) => (
                        <div
                          key={i}
                          className={`p-3 rounded-lg border text-xs ${
                            f.severity === "CRITICAL"
                              ? "bg-red-50 border-red-300 text-red-950"
                              : "bg-amber-50 border-amber-300 text-amber-950"
                          }`}
                        >
                          <div className="flex items-center justify-between font-bold">
                            <span className="flex items-center gap-1">
                              <span>{f.severity === "CRITICAL" ? "🚨" : "⚠️"}</span>
                              <span>{f.title}</span>
                            </span>
                            <span className="font-mono text-[10px] px-1.5 py-0.5 bg-white/80 rounded border">
                              {f.rule_id}
                            </span>
                          </div>
                          <p className="mt-1 text-slate-700 text-[11px] leading-relaxed">
                            {f.description}
                          </p>
                          <div className="mt-2 p-2 bg-white/70 rounded border border-slate-200 text-[11px] text-slate-800">
                            <strong>Recommendation:</strong> {f.recommendation}
                          </div>
                          <div className="mt-1 text-[10px] text-slate-500 italic">
                            Preliminary indicator. Human verification required.
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200 text-xs flex items-center gap-2">
                      <span>✅</span>
                      <span>{t("dossier.no_anomalies")}</span>
                    </div>
                  )}
                </div>

                {/* 3. Issuing-Authority Digital Bridge Cross-Check */}
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                      <span>🏛️</span> {t("dossier.authority_bridge")}
                    </h3>
                    {/* Simulated Source Badge */}
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                      🏷️ {t("simulated_source_badge")}
                    </span>
                  </div>

                  {curDoc?.source_verification ? (
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-slate-800">{curDoc.source_verification.authority_name}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            curDoc.source_verification.status === "VERIFIED"
                              ? "bg-emerald-100 text-emerald-800"
                              : curDoc.source_verification.status === "EXPIRED"
                              ? "bg-orange-100 text-orange-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {curDoc.source_verification.status}
                        </span>
                      </div>

                      <div className="text-[11px] text-slate-600">
                        {t("dossier.query_ref")}: <span className="font-mono text-slate-800 font-bold">{curDoc.source_verification.query_ref}</span>
                      </div>

                      <div className="p-2 bg-white rounded border border-slate-200 text-[11px] text-slate-700">
                        <strong>{t("dossier.official_finding")}:</strong> {curDoc.source_verification.discrepancy_details}
                      </div>

                      <div className="text-[10px] text-slate-400 flex justify-between">
                        <span>Timestamp: {curDoc.source_verification.verified_at}</span>
                        <span>Match Score: {curDoc.source_verification.match_score}%</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 p-2">
                      Automated repository link pending manual sub-registrar deed scrutiny.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: INSTITUTION APPLICANT PORTAL */}
        {/* ========================================================================= */}
        {activeTab === "INSTITUTION_PORTAL" && selectedApp && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Extension of Approval (EoA) Dossier Status — AY 2026-27
                  </h2>
                  <div className="text-xs text-slate-500">
                    Institution: <strong>{selectedApp.application?.institution?.name}</strong> (PID: {selectedApp.application?.institution?.permanent_id})
                  </div>
                </div>
                <span className="px-3 py-1 bg-blue-100 text-blue-900 text-xs font-bold rounded-lg border border-blue-200">
                  Category: {selectedApp.application?.category?.replace(/_/g, " ")}
                </span>
              </div>

              {/* Submission Checklist Items */}
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
                Mandatory Statutory Checklist Evaluation
              </h3>

              <div className="divide-y divide-slate-200 border rounded-xl overflow-hidden text-xs">
                {(selectedApp.checklist_evaluation?.checklist_items || []).map((item, i) => (
                  <div key={i} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white hover:bg-slate-50">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{item.title}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.status === "SATISFIED"
                              ? "bg-emerald-100 text-emerald-800"
                              : item.status === "MISSING"
                              ? "bg-red-100 text-red-800"
                              : item.status === "EXPIRED"
                              ? "bg-orange-100 text-orange-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                      <div className="text-slate-500 text-[11px]">{item.notes}</div>
                    </div>

                    {item.status !== "SATISFIED" && (
                      <button
                        onClick={() => {
                          const docObj = selectedApp.application?.documents?.find(d => d.id === item.document_id) || { id: item.document_id || "DOC-NEW", title: item.title };
                          setRectifyDoc(docObj);
                          setShowRectifyModal(true);
                        }}
                        className="bg-blue-800 hover:bg-blue-900 text-white font-medium px-3 py-1.5 rounded-lg text-xs whitespace-nowrap self-start sm:self-center"
                      >
                        Upload / Rectify 📤
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: INFRASTRUCTURE & GEOFENCE COMPLIANCE */}
        {/* ========================================================================= */}
        {activeTab === "INFRA_GEOFENCE" && selectedApp && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Campus Geotagged Infrastructure & Evidence Audit
                  </h2>
                  <div className="text-xs text-slate-500">
                    Haversine boundary geofencing, Laplacian blur detection, and AI Vision verification.
                  </div>
                </div>
                <span className="text-xs font-mono px-2 py-1 rounded bg-slate-100 border text-slate-700">
                  Geofence Tolerance: 350 meters
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {(selectedApp.application?.geotagged_evidence || []).map((ev) => (
                  <div key={ev.id} className="border border-slate-200 rounded-xl overflow-hidden shadow-sm bg-white">
                    <div className="h-44 bg-slate-800 text-white p-4 relative flex flex-col justify-between overflow-hidden">
                      <div className="absolute inset-0 opacity-25 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px]"></div>
                      <div className="relative z-10 flex justify-between items-start">
                        <span className="bg-black/60 px-2 py-1 rounded text-[11px] font-mono">
                          GPS: {ev.captured_gps?.lat?.toFixed(4)}, {ev.captured_gps?.lng?.toFixed(4)}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            ev.geofence_passed
                              ? "bg-emerald-500 text-white"
                              : "bg-red-500 text-white animate-pulse"
                          }`}
                        >
                          {ev.geofence_passed ? "GEOFENCE PASS" : "GEOFENCE BREACH (>350m)"}
                        </span>
                      </div>

                      <div className="relative z-10">
                        <h4 className="text-sm font-bold">{ev.title}</h4>
                        <div className="text-xs text-slate-300">
                          Deviation from campus centroid:{" "}
                          <strong className={ev.distance_deviation_meters > 350 ? "text-red-400 font-bold" : "text-emerald-400"}>
                            {ev.distance_deviation_meters} meters
                          </strong>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 space-y-3 text-xs">
                      <div className="p-2 bg-slate-50 rounded border text-slate-700 text-[11px]">
                        <strong>Audit Note:</strong> {ev.notes}
                      </div>

                      <div className="p-2 bg-amber-50 rounded border border-amber-200 text-amber-900 text-[11px]">
                        <strong>Advisory Recommendation:</strong>{" "}
                        {ev.geofence_passed
                          ? "Compliant facility evidence."
                          : "Recommend Expert Visiting Committee (EVC) Physical Inspection."}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: APH NORMS & CONFIG ADMIN */}
        {/* ========================================================================= */}
        {activeTab === "RULES_ADMIN" && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    AICTE Approval Process Handbook (APH) Regulatory Norms
                  </h2>
                  <div className="text-xs text-slate-500">
                    Configurable statutory thresholds for land norms, Faculty-Student Ratio (FSR), and cadre proportions.
                  </div>
                </div>
                <span className="text-xs bg-amber-100 text-amber-900 font-bold px-2.5 py-1 rounded border border-amber-200">
                  APH AY 2024-2027 Standards
                </span>
              </div>

              {rules && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                    <h3 className="font-bold text-slate-900 uppercase tracking-wider text-xs">
                      1. Minimum Land Norms (Acres)
                    </h3>
                    <div className="space-y-2">
                      {Object.entries(rules.land_norms_acres || {}).map(([cat, acres]) => (
                        <div key={cat} className="flex justify-between items-center p-2 bg-white rounded border">
                          <span className="font-medium text-slate-700">{cat.replace("_", " ")}</span>
                          <span className="font-bold font-mono text-blue-900">{acres} Acres</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                    <h3 className="font-bold text-slate-900 uppercase tracking-wider text-xs">
                      2. Faculty-Student Ratio (FSR)
                    </h3>
                    <div className="space-y-2">
                      {Object.entries(rules.fsr_norms || {}).map(([prog, ratio]) => (
                        <div key={prog} className="flex justify-between items-center p-2 bg-white rounded border">
                          <span className="font-medium text-slate-700">{prog.replace("_", " ")}</span>
                          <span className="font-bold font-mono text-blue-900">1 : {ratio}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 6: LIVE BENCHMARKING & EVALUATION METRICS */}
        {/* ========================================================================= */}
        {activeTab === "EVALUATION_METRICS" && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Live Model Evaluation & Benchmarking Dashboard
                  </h2>
                  <div className="text-xs text-slate-500">
                    Precision, recall, and time-saving metrics scored against 15 synthetic institutions with planted defects.
                  </div>
                </div>
                <button
                  onClick={fetchMetrics}
                  className="bg-slate-900 hover:bg-slate-800 text-white px-3 py-1.5 rounded-lg text-xs font-medium self-start sm:self-center"
                >
                  🔄 Recalculate Metrics
                </button>
              </div>

              {metrics && (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-center">
                      <div className="text-[11px] text-blue-700 font-medium">Precision</div>
                      <div className="text-xl font-bold text-blue-900 mt-0.5">{metrics.precision}%</div>
                    </div>
                    <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
                      <div className="text-[11px] text-emerald-700 font-medium">Recall</div>
                      <div className="text-xl font-bold text-emerald-900 mt-0.5">{metrics.recall}%</div>
                    </div>
                    <div className="p-3 bg-purple-50 border border-purple-200 rounded-xl text-center">
                      <div className="text-[11px] text-purple-700 font-medium">F1 Score</div>
                      <div className="text-xl font-bold text-purple-900 mt-0.5">{metrics.f1_score}%</div>
                    </div>
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-center">
                      <div className="text-[11px] text-amber-700 font-medium">OCR Extraction</div>
                      <div className="text-xl font-bold text-amber-900 mt-0.5">{metrics.extraction_accuracy}%</div>
                    </div>
                    <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-center">
                      <div className="text-[11px] text-teal-700 font-medium">Avg Verify Speed</div>
                      <div className="text-xl font-bold text-teal-900 mt-0.5">{metrics.average_verification_time_seconds}s</div>
                    </div>
                    <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-center">
                      <div className="text-[11px] text-rose-700 font-medium">Effort Saved</div>
                      <div className="text-xl font-bold text-rose-900 mt-0.5">{metrics.estimated_manual_effort_saved_percent}%</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 7: CRYPTOGRAPHIC AUDIT CHAIN */}
        {/* ========================================================================= */}
        {activeTab === "AUDIT_TRAIL" && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Append-Only Cryptographic Audit Trail
                  </h2>
                  <div className="text-xs text-slate-500">
                    SHA-256 hash-chained immutable event log. Every OCR extraction, external API check, and officer decision is tamper-sealed.
                  </div>
                </div>

                {auditChainStatus && (
                  <span className="px-3 py-1 rounded-lg text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    Audit Chain 100% Mathematically Verified ({auditChainStatus.total_records_verified} blocks)
                  </span>
                )}
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden text-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-100 text-slate-700 font-semibold">
                    <tr>
                      <th className="p-3">Log ID & Timestamp</th>
                      <th className="p-3">Actor</th>
                      <th className="p-3">Action</th>
                      <th className="p-3">Event Details</th>
                      <th className="p-3 text-right">Cryptographic SHA-256 Signature</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {auditLogs.map((log) => (
                      <tr key={log.log_id} className="hover:bg-slate-50">
                        <td className="p-3 font-mono">
                          <span className="font-bold text-slate-900 block">{log.log_id}</span>
                          <span className="text-[10px] text-slate-400">{log.timestamp}</span>
                        </td>
                        <td className="p-3 font-medium text-slate-800">{log.actor}</td>
                        <td className="p-3 font-mono text-[11px] text-blue-900">{log.action}</td>
                        <td className="p-3 text-slate-600 max-w-xs">{log.details}</td>
                        <td className="p-3 text-right font-mono text-[10px] text-slate-500">
                          <span className="px-1.5 py-0.5 bg-slate-100 rounded border">
                            {log.hash_signature?.slice(0, 16)}...
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ========================================================================= */}
      {/* MODAL: OFFICER SCRUTINY DECISION CONFIRMATION */}
      {/* ========================================================================= */}
      {showDecisionModal && selectedApp && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-1.5">
                <span>✍️</span> {t("officer_modal.title")}
              </h3>
              <button
                onClick={() => setShowDecisionModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-900">
              {t("officer_modal.mandate")}
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">{t("officer_modal.select_decision")}</label>
                <select
                  value={decisionType}
                  onChange={(e) => setDecisionType(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg font-medium text-slate-800 focus:ring-2 focus:ring-blue-600"
                >
                  <option value="APPROVED">{t("officer_modal.approve_opt")}</option>
                  <option value="DEFICIENCY_NOTICE">{t("officer_modal.deficiency_opt")}</option>
                  <option value="EVC_PHYSICAL_INSPECTION">{t("officer_modal.evc_opt")}</option>
                  <option value="REJECTED">{t("officer_modal.reject_opt")}</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  {t("officer_modal.remarks_label")} <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows="4"
                  placeholder={t("officer_modal.remarks_placeholder")}
                  value={decisionRemarks}
                  onChange={(e) => setDecisionRemarks(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg text-slate-800 focus:ring-2 focus:ring-blue-600"
                ></textarea>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button
                onClick={() => setShowDecisionModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={handleOfficerDecisionSubmit}
                className="px-4 py-2 rounded-lg text-xs font-bold bg-blue-900 hover:bg-blue-950 text-white shadow-md"
              >
                {t("officer_modal.seal_btn")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: INSTITUTION RECTIFICATION SUBMISSION */}
      {/* ========================================================================= */}
      {showRectifyModal && rectifyDoc && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-1.5">
                <span>📤</span> Rectify Deficient Document
              </h3>
              <button
                onClick={() => setShowRectifyModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-slate-600">
              Rectifying document: <strong>{rectifyDoc.title}</strong>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Replacement File Name:</label>
                <input
                  type="text"
                  placeholder="e.g. Renewed_Fire_NOC_2026_Official.pdf"
                  value={rectifyFileName}
                  onChange={(e) => setRectifyFileName(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Institutional Explanation & Justification:</label>
                <textarea
                  rows="4"
                  placeholder="Explain actions taken to resolve deficiency (e.g. obtained official renewal, updated deed)..."
                  value={rectifyExplanation}
                  onChange={(e) => setRectifyExplanation(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg text-slate-800 focus:ring-2 focus:ring-blue-600"
                ></textarea>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button
                onClick={() => setShowRectifyModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleRectificationSubmit}
                className="px-4 py-2 rounded-lg text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-md"
              >
                Submit Rectification 📤
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Official Government Footer */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-6 border-t border-slate-800 mt-auto">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <div className="text-slate-200 font-bold">{t("app_title")} — {t("subtitle")}</div>
            <div className="text-[11px] text-slate-500">
              {t("org_title")} | {t("govt_title")}
            </div>
          </div>
          <div className="text-[11px] text-amber-400 font-mono">
            {t("advisory_guardrail_active")}
          </div>
        </div>
      </footer>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
