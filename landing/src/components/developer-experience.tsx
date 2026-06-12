"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Terminal, Copy, CheckCircle2 } from "lucide-react";

export function DeveloperExperience() {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("python");

  const tabs = [
    { id: "python", label: "Python SDK" },
    { id: "register", label: "Model Registration" },
    { id: "retrain", label: "Retraining Callback" },
    { id: "telemetry", label: "Telemetry Logging" },
  ];

  const codeSnippets: Record<string, string> = {
    python: `import driftguard as dg

# Initialize the DriftGuard client
client = dg.Client(api_key="dg_prod_xxx")

# Wrap your existing model
model = client.wrap_model(
    model_instance=my_xgboost_model,
    model_name="fraud_detection_v1",
    version="1.0.0",
    features=["amount", "location", "time", "device_type"]
)`,
    register: `from driftguard.schema import ModelSchema, FeatureType

# Define strict schema for production
schema = ModelSchema(
    features={
        "amount": FeatureType.FLOAT,
        "location": FeatureType.CATEGORICAL,
        "time": FeatureType.TIMESTAMP,
        "device_type": FeatureType.CATEGORICAL
    },
    prediction=FeatureType.FLOAT
)

client.register_schema("fraud_detection_v1", schema)`,
    retrain: `@client.on_drift_detected(model_name="fraud_detection_v1", threshold=0.5)
def trigger_retraining(drift_report):
    print(f"Drift detected! Score: {drift_report.score}")
    
    # Kick off your MLflow pipeline
    run_id = mlflow.run(
        "git://github.com/org/retrain-pipeline.git",
        parameters={"dataset_window": "last_30_days"}
    )
    
    return {"status": "retraining_started", "run_id": run_id}`,
    telemetry: `# In your fastAPI / Flask serving endpoint

@app.post("/predict")
async def predict(data: dict):
    # Log telemetry asynchronously to DriftGuard
    prediction = model.predict(data)
    
    client.log_prediction(
        model_name="fraud_detection_v1",
        features=data,
        prediction=prediction,
        ground_truth=None # Logged later via delayed labels
    )
    
    return {"prediction": prediction}`
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(codeSnippets[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-16 px-4 bg-background border-b-4 border-foreground">
      <div className="container mx-auto grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <div className="inline-block bg-secondary text-foreground font-sans font-black px-4 py-1 border-4 border-foreground brutal-shadow-sm mb-4 uppercase text-lg">
            Developer First
          </div>
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter mb-6">
            Built for <span className="text-secondary glitch-text inline-block" data-text="Engineers">Engineers</span>
          </h2>
          <p className="text-lg md:text-xl font-sans mb-6 max-w-lg">
            Integrate DriftGuard into your existing stack in minutes. Our Python SDK is designed to be completely unobtrusive to your actual inference code.
          </p>

          <div className="flex flex-col gap-4 font-sans font-bold uppercase w-full max-w-sm">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`text-left px-6 py-4 border-4 border-foreground transition-all flex items-center justify-between ${
                  activeTab === tab.id 
                  ? 'bg-secondary text-foreground brutal-shadow translate-x-2' 
                  : 'bg-surface text-foreground hover:bg-background'
                }`}
              >
                {tab.label}
                {activeTab === tab.id && <div className="w-3 h-3 bg-background border-2 border-foreground rounded-full"></div>}
              </button>
            ))}
          </div>
        </div>

        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="border-4 border-foreground brutal-shadow bg-[#0d1117] relative"
        >
          {/* Terminal Window Header */}
          <div className="bg-surface border-b-4 border-foreground px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 border-2 border-foreground rounded-full"></div>
              <div className="w-3 h-3 bg-amber-500 border-2 border-foreground rounded-full"></div>
              <div className="w-3 h-3 bg-green-500 border-2 border-foreground rounded-full"></div>
            </div>
            <div className="font-sans text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Terminal className="w-4 h-4" /> {activeTab}.py
            </div>
          </div>

          <div className="p-5 overflow-x-auto relative group">
            <button 
              onClick={handleCopy}
              className="absolute top-4 right-4 p-2 bg-surface border-2 border-foreground brutal-button opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label="Copy code"
            >
              {copied ? <CheckCircle2 className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5 text-foreground" />}
            </button>
            <pre className="font-sans text-sm md:text-base leading-relaxed text-[#e6edf3]">
              <code>
                {codeSnippets[activeTab].split('\n').map((line, i) => (
                  <div key={i} className="flex">
                    <span className="text-[#7d8590] w-8 shrink-0 select-none">{i + 1}</span>
                    <span dangerouslySetInnerHTML={{
                      __html: line.replace(/(#.*)|(".*?")|\b(import|from|as|def|async|await|return)\b|\b(driftguard|dg|mlflow)\b|(= )/g, (match, comment, str, keyword, special, eq) => {
                        if (comment) return `<span class="text-[#8b949e]">${comment}</span>`;
                        if (str) return `<span class="text-[#a5d6ff]">${str}</span>`;
                        if (keyword) return `<span class="text-[#ff7b72]">${keyword}</span>`;
                        if (special) return `<span class="text-[#79c0ff]">${special}</span>`;
                        if (eq) return `<span class="text-[#ff7b72]">${eq}</span>`;
                        return match;
                      })
                    }} />
                  </div>
                ))}
              </code>
            </pre>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
