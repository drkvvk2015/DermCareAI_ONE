from dermatology.procedures import ProcedureRecord, validate_procedure

def test_biopsy_record():
    validate_procedure(ProcedureRecord(
        "biopsy","left forearm","changing lesion","CONS-1","doctor-1",
        "2026-09-22T00:00:00+00:00"
    ))

def test_unknown_procedure_is_rejected():
    try:
        validate_procedure(ProcedureRecord("unknown","arm","test","CONS-1","doctor-1","2026-09-22"))
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported procedures must be rejected")
