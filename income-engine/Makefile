.PHONY: setup data train report test app api all
export PYTHONPATH := src

setup:   ; pip install -r requirements.txt
data:    ; python -m ite.synth --n 8000 --seed 42 --out data
train:   ; python -m ite.train
report:  ; python -m ite.report
test:    ; python -m pytest -q
app:     ; streamlit run app/streamlit_app.py
api:     ; uvicorn api.main:app --host 0.0.0.0 --port 8000
all: data train report test
