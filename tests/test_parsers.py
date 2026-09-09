import pytest
from src.parsers.solr_parser import SolrLogParser
from src.parsers.gc_parser import GCLogParser
from src.models.events import LogSource, Severity, ParseStatus


def test_solr_log_parser_valid_request():
    parser = SolrLogParser()
    line = (
        "2026-09-08 10:00:00.123 INFO  (qtp108941827-100) [solr-node-1:8983_solr ecommerce_shard1_replica_n1] "
        "o.a.s.c.S.Request [ecommerce] webapp=/solr path=/select params={q=category:electronics} hits=150 status=0 QTime=45"
    )
    event = parser.parse_line(line, default_node_id="solr-node-1")

    assert event is not None
    assert event.source == LogSource.SOLR
    assert event.severity == Severity.INFO
    assert event.node_id == "solr-node-1"
    assert event.metrics.get("qtime_ms") == 45.0
    assert event.metrics.get("hits") == 150.0
    assert event.parse_status == ParseStatus.PARSED


def test_solr_log_parser_error_line():
    parser = SolrLogParser()
    line = (
        "2026-09-08 10:05:00.000 ERROR (qtp108941827-101) [solr-node-2:8983_solr catalog_shard1_replica_n2] "
        "o.a.s.h.RequestHandlerBase Request execution failed or timed out. path=/select QTime=5120"
    )
    event = parser.parse_line(line, default_node_id="solr-node-2")

    assert event is not None
    assert event.severity == Severity.ERROR
    assert event.metrics.get("qtime_ms") == 5120.0
    assert event.event_type == "SOLR_ERROR"


def test_solr_log_parser_malformed():
    parser = SolrLogParser()
    line = "Random unformatted error message without timestamp"
    event = parser.parse_line(line, default_node_id="solr-node-1")

    assert event is not None
    assert event.parse_status == ParseStatus.PARTIALLY_PARSED
    assert event.event_type == "UNSTRUCTURED_SOLR_LOG"


def test_gc_log_parser_minor_gc():
    parser = GCLogParser()
    line = (
        "2026-09-08T10:00:00.000+0000: [solr-node-1] [GC (Allocation Failure) "
        "[PSYoungGen: 524288K->32768K(611840K)] 1048576K->557056K(2097152K), 0.018 secs]"
    )
    event = parser.parse_line(line, default_node_id="solr-node-1")

    assert event is not None
    assert event.source == LogSource.JVM_GC
    assert event.node_id == "solr-node-1"
    assert event.metrics.get("pause_duration_ms") == 18.0
    assert event.metrics.get("heap_after_mb") == pytest.approx(544.0, 1.0)
    assert event.parse_status == ParseStatus.PARSED


def test_gc_log_parser_full_gc_long_pause():
    parser = GCLogParser()
    line = (
        "2026-09-08T10:05:00.000+0000: [solr-node-2] [Full GC (Ergonomics) "
        "[PSYoungGen: 590000K->580000K(600000K)] [PSOldGen: 1460000K->1440000K(1497152K)] "
        "2050000K->2020000K(2097152K), 4.850 secs]"
    )
    event = parser.parse_line(line, default_node_id="solr-node-2")

    assert event is not None
    assert event.event_type == "JVM_FULL_GC"
    assert event.severity == Severity.ERROR
    assert event.metrics.get("pause_duration_ms") == 4850.0
    assert event.metrics.get("heap_occupancy_pct") > 90.0
