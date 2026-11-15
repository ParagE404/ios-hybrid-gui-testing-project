source .venv/bin/activate
appium

python spikes/demo_watch.py experiments/raw/demo.jsonl

python -m engine.cli run benchmark/scenarios/tb-07.yaml --config scripted --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands --log experiments/raw/demo.jsonl 2>/dev/null
python -m engine.cli run benchmark/scenarios/tb-07.yaml --config a11y --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands --log experiments/raw/demo.jsonl 2>/dev/null
python -m engine.cli run benchmark/scenarios/tb-07.yaml --config hybrid --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands --log experiments/raw/demo.jsonl 2>/dev/null
python -m engine.cli run benchmark/scenarios/su-02.yaml --config hybrid --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands --log experiments/raw/demo.jsonl 2>/dev/null
python -m engine.cli run benchmark/scenarios/su-08.yaml --config hybrid --condition perturbed --device "iPhone 17" --bundle co.pointfree.SyncUps --log experiments/raw/demo.jsonl
python -m engine.cli run benchmark/scenarios/tb-07.yaml --config hybrid --condition perturbed --device "iPhone 17" --bundle uk.ac.city.parag.Errands
