# wirebackup2txt
Extracts a Wire for desktop backup file into text files, one per conversation

## Requirements
Python 2.7, tested on Mac only

## Usage

Use Wire for desktop to get a backup of your conversations. Clone this repo, then run

```
python src/wirebackup2txt.py -e <email address> -p <password> [-d <destination>] <backup file>
```

