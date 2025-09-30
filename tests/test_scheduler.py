from src.scheduler import load_classes

def test_load_classes():
    df = load_classes("data/classes.csv")
    assert not df.empty
    assert "course_code" in df.columns
