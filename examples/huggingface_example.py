"""
DriftGuard SDK — HuggingFace text classification example.
Demonstrates wrapping an NLP text classification pipeline,
hashing text string inputs into tracking coordinates, and identifying distribution drift on text themes.
"""
import os
import sys
import time

# Ensure project modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import transformers
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from driftguard import DriftGuard

# Setup Mock Pipeline if transformers is not locally installed
if TRANSFORMERS_AVAILABLE:
    nlp_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
else:
    class MockNLPPipeline:
        def __call__(self, text, *args, **kwargs):
            # Return standard HF format
            return [{"label": "POSITIVE", "score": 0.985}]
        def predict(self, text, *args, **kwargs):
            return self.__call__(text)
            
    nlp_pipeline = MockNLPPipeline()

def main():
    print("====================================================")
    print("Step 1: Loading HuggingFace Sentiment Analysis pipeline...")
    print("HuggingFace pipeline initialized successfully!")

    # 2. Setup DriftGuard
    print("\nStep 2: Wrapping HuggingFace pipeline with DriftGuard SDK...")
    dg = DriftGuard(
        model_id="huggingface-sentiment-classifier",
        drift_threshold=0.15,
        auto_retrain=False
    )
    
    # Wrap pipeline callable
    model = dg.wrap(nlp_pipeline)
    print("HuggingFace pipeline wrapped and active!")

    # 3. Simulate Stable sentiment predictions (Standard English short comments)
    print("\nStep 3: Streaming standard stable sentiments (Praise reviews)...")
    stable_comments = [
        "This product is absolutely amazing! I highly recommend it.",
        "Excellent support and stellar performance. Five stars!",
        "Very clean interface and robust configurations.",
        "Delightful customer experience. Will purchase again.",
        "Simple, fast, and does exactly what it promises."
    ] * 10 # 50 samples

    for comment in stable_comments:
        # Call model directly (Huggingface standard)
        res = model(comment)
        
    print(f"Stable comments processed. Global Drift Score: {dg.drift_detector.global_drift_score:.4f}")

    # 4. Simulate Shifted Input Texts (Sudden change to long gibberish or spam comments)
    print("\nStep 4: Simulating text distribution shift (Gibberish/Spam theme drift)...")
    drifted_comments = [
        "BUY NOW!!! CHEAP PHARMACEUTICALS AND DISCOUNT COUPONS AT WWW.SPAM.COM!!!",
        "fhjsdka hfjdksla quryeiwoqp mzvnxbcz asdfghjkl qwertyuiop",
        "!!! SPAM CONTEST WINNER !!! CLICK HERE NOW TO CLAIM YOUR ONE MILLION DOLLARS",
        "asdfghjkl; zxcvbnm,./ qwertyuiop[] 1234567890",
        "FREE MONEY FREE TOKEN FREE COINS SIGN UP TODAY"
    ] * 5 # 25 samples

    drifted_scores = []
    for comment in drifted_comments:
        res = model(comment)
        drift_score = dg.drift_detector.global_drift_score
        drifted_scores.append(drift_score)
        
        if drift_score > dg.drift_threshold:
            print(f"Drift Detected! Text payload: '{comment[:40]}...' | Score: {drift_score:.4f}")

    print(f"\nShifted comments processed. Peak Drift Score: {max(drifted_scores):.4f}")
    print("====================================================")

if __name__ == "__main__":
    main()
