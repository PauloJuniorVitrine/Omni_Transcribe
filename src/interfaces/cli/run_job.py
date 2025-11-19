from __future__ import annotations

import argparse
from pathlib import Path

from application.controllers.job_controller import JobController
from domain.entities.value_objects import EngineType
from infrastructure.container import get_container


def main() -> None:
    parser = argparse.ArgumentParser(description="Processar jobs do TranscribeFlow")
    parser.add_argument("--job-id", help="ID do job existente")
    parser.add_argument("--file", help="Arquivo de áudio para criar um novo job")
    parser.add_argument("--profile", default="geral", help="Perfil editorial")
    parser.add_argument("--engine", default=None, help="Engine (openai/local)")
    args = parser.parse_args()

    container = get_container()
    job_controller = JobController(
        job_repository=container.job_repository,
        create_job_use_case=container.create_job_use_case,
        pipeline_use_case=container.pipeline_use_case,
        retry_use_case=container.retry_use_case,
    )

    engine_value = args.engine or container.settings.asr_engine
    engine = EngineType(engine_value)

    job_id = args.job_id
    if args.file:
        path = Path(args.file)
        if not path.exists():
            raise SystemExit(f"Arquivo {path} não encontrado.")
        job = job_controller.ingest_file(path, args.profile, engine)
        job_id = job.id
        print(f"Job criado: {job_id}")

    if not job_id:
        raise SystemExit("Informe --job-id ou --file.")

    job_controller.process_job(job_id)
    print(f"Pipeline concluído para {job_id}")


if __name__ == "__main__":
    main()
