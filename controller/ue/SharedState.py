from MetricsClient import MetricsClient

class SharedState:
    process_list = []
    attack_args = []
    cli_args = None
    ue_index = 1
    metrics_client = MetricsClient()
