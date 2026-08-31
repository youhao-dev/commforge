from commforge.database.database import create_database_engine, create_session_factory, initialize_database
from commforge.database.models import CommunicationModel
from commforge.repositories.repositories import CommunicationRepository


def test_sqlite_repository_crud() -> None:
    engine = create_database_engine(":memory:")
    initialize_database(engine)
    repository = CommunicationRepository(create_session_factory(engine))
    entity = repository.add(
        CommunicationModel(
            name="Test UDP", communication_type="UDP", config_json='{"local_port": 9000}'
        )
    )
    assert entity.id is not None
    assert repository.get(entity.id).name == "Test UDP"
    repository.update(entity.id, name="Updated UDP")
    assert repository.get(entity.id).name == "Updated UDP"
    assert len(repository.list_all()) == 1
    assert repository.delete(entity.id)
    assert repository.get(entity.id) is None
