import pandas as pd, streamlit as st
from itertools import combinations
from google import genai

st.set_page_config(page_title="تداخلاتي", page_icon="💊")
st.markdown("<style>.stApp{direction:rtl}</style>", unsafe_allow_html=True)
st.title("💊 تداخلاتي")
st.caption("فاحص التداخلات الدوائية")

sheet_id = "1MzsYnkysJ3pYkVJFlAtFqRhAlazs7iK6rZnwzUltCl4"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
load = st.cache_data(ttl=600)(lambda: pd.read_csv(url))
raw = load().dropna(subset=["drug1", "drug2"])
raw = raw if "verified" in raw.columns else raw.assign(verified="")
df = raw[raw["verified"].astype(str).str.strip().str.lower() == "yes"].copy()
df = df.assign(drug1=df["drug1"].astype(str).str.strip(), drug2=df["drug2"].astype(str).str.strip(), severity=df["severity"].astype(str).str.strip())

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
order = {"Danger": 0, "Caution": 1, "Safe": 2}
icons = {"Danger": "🔴", "Caution": "🟡", "Safe": "🟢"}
drugs = sorted(set(df["drug1"]).union(set(df["drug2"])))
note = "\n\n⚠️ للتوعية والتعليم فقط، ولا يغني عن استشارة الطبيب أو الصيدلاني."
rules = "انت مساعد لتطبيق تداخلات دوائية لطلبة صيدلة. جاوب بالعربي بلهجة عراقية مبسطة وبشكل مختصر. اعتمد فقط على البيانات التالية ولا تضف أي معلومة طبية من عندك، ولا تعطي جرعات ولا تشخص. اذا السؤال ما تغطيه البيانات كول: ما لكيت معلومة بالقاعدة عن هذا السؤال، راجعي الصيدلاني أو الطبيب.\n\nالبيانات (دواء1 + دواء2 | الخطورة | التأثير | الأعراض | التوصية):\n"

def find(a, b): return next((r for _, r in df.iterrows() if {r["drug1"].lower(), r["drug2"].lower()} == {a.lower(), b.lower()}), None)
def find_all(chosen): return sorted([r for r in (find(a, b) for a, b in combinations(chosen, 2)) if r is not None], key=lambda r: order.get(r["severity"], 3))
def line(r): return "**" + icons.get(r["severity"], "⚪") + " " + r["drug1"] + " + " + r["drug2"] + " → " + r["severity"] + "**\n\n- Effect: " + str(r["effect"]) + "\n- Symptoms: " + str(r["symptoms"]) + "\n- Recommendation: " + str(r["recommendation"])
def report(chosen): return "اختاري دوائين على الأقل" if len(chosen) < 2 else ("\n\n---\n\n".join(line(r) for r in find_all(chosen)) or "ما لكيت تداخل مسجل بين هذي الأدوية (وهذا لا يعني إنها آمنة!)")
def context(): return "\n".join(str(r["drug1"]) + " + " + str(r["drug2"]) + " | " + str(r["severity"]) + " | " + str(r["effect"]) + " | " + str(r["symptoms"]) + " | " + str(r["recommendation"]) for _, r in df.iterrows())

def ask(q):
    if not q.strip(): return "اكتبي سؤالج أول"
    if len(df) == 0: return "ماكو تداخلات مراجعة بالقاعدة هسه."
    try: return client.models.generate_content(model="gemini-1.5-flash", contents=rules + context() + "\n\nالسؤال: " + q).text
    except Exception: return "السيرفر مشغول هسه، جربي بعد شوية."

tab1, tab2 = st.tabs(["فحص التداخلات", "اسألي"])
chosen = tab1.multiselect("اختاري الأدوية (2 أو أكثر)", drugs)
tab1.markdown(report(chosen) + note)
q = tab2.text_area("اسألي عن التداخلات الدوائية")
go = tab2.button("اسألي")
tab2.markdown(ask(q) + note if go else "")
st.caption("عدد التداخلات المراجَعة: " + str(len(df)))
