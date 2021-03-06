"""
This module defines a trainer for auto-regressive sequential models.
"""

# Externals
import torch
from torch.nn.parallel import DistributedDataParallel

# Locals
from .basic import BasicTrainer
import utils.metrics

class AutoRegressiveTrainer(BasicTrainer):
    """Trainer code for basic classification problems."""

    def __init__(self, **kwargs):
        super(AutoRegressiveTrainer, self).__init__(**kwargs)

    def train_epoch(self, data_loader):
        """Train for one epoch"""

        self.model.train()

        # Reset metrics
        sum_loss = 0
        utils.metrics.reset_metrics(self.metrics)

        # Loop over training batches
        for i, batch in enumerate(data_loader):
            batch = batch.to(self.device)
            self.model.zero_grad()
            batch_input, batch_target = batch[:,:-1], batch[:,1:]
            batch_output = self.model(batch_input)
            batch_loss = self.loss_func(batch_output, batch_target)
            batch_loss.backward()
            self.optimizer.step()
            sum_loss += batch_loss.item()
            utils.metrics.update_metrics(self.metrics, batch_output, batch_target)
            self.logger.debug('batch %i loss %.3f', i, batch_loss.item())
            self.logger.debug('cuda mem %g max %g',
                              torch.cuda.memory_allocated()/1024**3,
                              torch.cuda.max_memory_allocated()/1024**3)

        train_loss = sum_loss / (i + 1)
        metrics_summary = utils.metrics.get_results(self.metrics)
        self.logger.debug('Processed %i batches' % (i + 1))

        # Return summary
        return dict(loss=train_loss, **metrics_summary)

    @torch.no_grad()
    def evaluate(self, data_loader):
        """"Evaluate the model"""

        self.model.eval()

        # Reset metrics
        sum_loss = 0
        utils.metrics.reset_metrics(self.metrics)

        # Loop over batches
        for i, batch in enumerate(data_loader):
            batch = batch.to(self.device)
            batch_input, batch_target = batch[:,:-1], batch[:,1:]
            batch_output = self.model(batch_input)
            batch_loss = self.loss_func(batch_output, batch_target).item()
            sum_loss += batch_loss
            utils.metrics.update_metrics(self.metrics, batch_output, batch_target)
            self.logger.debug('batch %i loss %.3f', i, batch_loss)

        # Summarize validation metrics
        metrics_summary = utils.metrics.get_results(self.metrics)

        valid_loss = sum_loss / (i + 1)
        self.logger.debug('Processed %i samples in %i batches',
                          len(data_loader.sampler), i + 1)

        # Return summary
        return dict(loss=valid_loss, **metrics_summary)

def get_trainer(**kwargs):
    return AutoRegressiveTrainer(**kwargs)

def _test():
    t = AutoRegressiveTrainer(output_dir='./')
    t.build_model()
