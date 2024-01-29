import optuna
import torch
from transformers import AutoModel, AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainingArguments
import pandas as pd
from datasets import Dataset
import json

# Read JSONL file line by line
def read_jsonl(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return [json.loads(line) for line in lines]

# Load your custom dataset
df_train = pd.json_normalize(read_jsonl('../test/dev.jsonl'))
df_dev = pd.json_normalize(read_jsonl('../test/test.jsonl'))

# Convert pandas DataFrame to datasets.Dataset
train_dataset = Dataset.from_pandas(df_train)
dev_dataset = Dataset.from_pandas(df_dev)

# Define the model and optimizer
def objective(trial):
    # Define hyperparameter search space
    learning_rate = trial.suggest_loguniform('learning_rate', 1e-5, 1e-3)
    weight_decay = trial.suggest_loguniform('weight_decay', 1e-8, 1e-5)
    num_train_epochs = trial.suggest_int('num_train_epochs', 3, 5)
    batch_size = trial.suggest_categorical('batch_size', [2, 3, 4])

    # Load pretrained model and tokenizer
    model_name = '/root/autodl-tmp/models/AI-ModelScope/Mistral-7B-v0.1'
    model = AutoModel.from_pretrained(model_name, num_labels=2).eval()
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    # Define optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="./output",
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=1,
        logging_steps=100,
        num_train_epochs=num_train_epochs,
        evaluation_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        save_strategy="epoch",  # Set the save strategy to "epoch"
)


    # Define trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=dev_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorForSeq2Seq(tokenizer),  # Use DataCollatorForSeq2Seq for seq2seq tasks
        compute_metrics=None,  # Add a metric function if needed
    )

    # Train the model
    trainer.train()

    # Evaluate and return the performance metric
    results = trainer.evaluate()
    return results['eval_loss']  # Change 'eval_loss' to the actual metric you want to optimize

# Run hyperparameter search
study = optuna.create_study(direction='minimize')  # Adjust direction based on the metric you want to optimize
study.optimize(objective, n_trials=100)

# Output the best trial and its parameters
print('Best trial:')
trial = study.best_trial
print('  Value: {}'.format(trial.value))
print('  Params: ')
for key, value in trial.params.items():
    print('    {}: {}'.format(key, value))