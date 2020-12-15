def manifest_key(args, batch_number: int, end_offset: int, start_offset: int) -> str:
    start_topics = ["db.calculator.calculationParts", "db.core.journal", "db.core.wizard", "db.agent-core.agentToDo"]
    end_topics = ["db.agent-core.agentToDo", "db.core.wizard", "db.core.journal", "db.calculator.calculationParts"]
    start_topic = start_topics[batch_number % 4]
    end_topic = end_topics[batch_number % 4]
    partition = batch_number % 10
    return f"{args.prefix}/{start_topic}_{partition}_{start_offset}-{end_topic}_{partition}_{end_offset}.txt"


def manifest_batch(args, batch_number):
    batch = [manifest_record(args.database, args.collection, batch_number, record_number) for record_number in
             range(args.record_count)]
    accumulated = "\n".join(batch)
    return f"{accumulated}\n"


def manifest_record(database: str, collection: str, batch_number: int, record_number: int):
    return f"{database}|{collection}|{batch_number}|{record_number}"
