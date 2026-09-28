from .base import TrainingBackend


class ExperimentalChatterboxTraining(TrainingBackend):
    """Extension point only: no validated Turbo training workflow is bundled."""
    def prepare_dataset(self, source, destination):
        raise NotImplementedError("Turbo training is not implemented.")
    def train(self, dataset, **settings):
        raise NotImplementedError("Turbo training is not implemented.")
    def save_checkpoint(self, path):
        raise NotImplementedError("Turbo training is not implemented.")
    def load_checkpoint(self, path):
        raise NotImplementedError("Turbo training is not implemented.")
