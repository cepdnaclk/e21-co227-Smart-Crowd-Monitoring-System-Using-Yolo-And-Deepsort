from backend_logic import filter_person_detections


def test_filter_person_detections_by_conf_and_class():
    # (xywh, conf, class_id)
    detections = [
        ((0, 0, 10, 10), 0.9, 0),  # person high conf
        ((0, 0, 10, 10), 0.3, 0),  # person low conf (filtered out)
        ((0, 0, 10, 10), 0.8, 1),  # not a person (filtered out)
    ]
    class_names = {0: "person", 1: "car"}

    out = filter_person_detections(detections, class_names=class_names, min_conf=0.4)
    assert len(out) == 1
    xywh, conf, cls_id = out[0]
    assert conf == 0.9 and cls_id == 0
