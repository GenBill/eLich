from .dataset import PrimeRotationDataset

import torch
import torch.nn.parallel
from tqdm import tqdm
import time
import copy
import warnings
warnings.filterwarnings('ignore')

# General Code for supervised train
def rotatrain(model, fc_layer, dataloaders, criterion, optimizer, scheduler, 
    device, checkpoint_path, file, saveinterval=1, last_epochs=0, num_epochs=20):

    since = time.time()
    best_acc = 0.0

    for epoch in range(last_epochs, last_epochs+num_epochs):
        print('\nEpoch {}/{} \n'.format(epoch, last_epochs+num_epochs - 1))
        file.write('\nEpoch {}/{} \n'.format(epoch, last_epochs+num_epochs - 1))
        file.write('-' * 10)
        file.write('\n')
        file.flush()

        # Each epoch has a training and validation phase
        for phase in ['train', 'test']:
            if phase == 'train':
                model.train()  # Set model to training mode
                fc_layer.train()
            else:
                model.eval()  # Set model to evaluate mode
                fc_layer.eval()

            running_loss = 0.0
            running_corrects = 0
            n_samples = 0

            end = time.time()

            # Iterate over data.
            for _, (inputs, labels) in enumerate(tqdm(dataloaders[phase])):
                inputs = inputs.to(device)
                labels = labels.to(device)
                # zero the parameter gradients
                optimizer.zero_grad()
                batchSize = labels.size(0)
                n_samples += batchSize

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = fc_layer(model(inputs))
                    loss = criterion(outputs, labels)
                    # backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()
                        scheduler.step()

                # statistics
                running_loss += loss.item() * labels.size(0)
                pred_top_1 = torch.topk(outputs, k=1, dim=1)[1]
                running_corrects += pred_top_1.eq(labels.view_as(pred_top_1)).int().sum().item()

            # Metrics
            top_1_acc = running_corrects / n_samples
            epoch_loss = running_loss / n_samples
            print('{} Loss: {:.6f} Top 1 Acc: {:.6f} \n'.format(phase, epoch_loss, top_1_acc))

            file.write('{} Loss: {:.6f} Top 1 Acc: {:.6f} \n'.format(phase, epoch_loss, top_1_acc))
            file.flush()

            # deep copy the model
            if phase == 'test' and top_1_acc > best_acc:
                best_acc = top_1_acc
                best_model_wts = copy.deepcopy(model.state_dict())
                best_fc_wts = copy.deepcopy(fc_layer.state_dict())
        if (epoch+1) % saveinterval == 0:
            torch.save(model.state_dict(), '%s/model_epoch_%d.pth' % (checkpoint_path, epoch))
            torch.save(fc_layer.state_dict(), '%s/fc_epoch_%d.pth' % (checkpoint_path, epoch))

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s \n'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best test Acc: {:4f} \n'.format(best_acc))
    file.write('Training complete in {:.0f}m {:.0f}s \n'.format(time_elapsed // 60, time_elapsed % 60))
    file.write('Best test Acc: {:4f} \n'.format(best_acc))
    file.flush()

    # load best model weights
    model.load_state_dict(best_model_wts)
    fc_layer.load_state_dict(best_fc_wts)
    return model, fc_layer

def rotaloader(data_root, data_pre_transforms, data_post_transforms, batch_size, num_workers):
    image_datasets = {
        x: PrimeRotationDataset(x, data_root, data_pre_transforms[x], data_post_transforms[x])
        for x in ['train', 'test']
    }
    assert image_datasets
    dataloaders = {
        x: torch.utils.data.DataLoader(
            image_datasets[x], batch_size=batch_size,
            pin_memory=True, shuffle=True, num_workers=num_workers
        ) for x in ['train', 'test']}
    # dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'test']}
    return dataloaders

