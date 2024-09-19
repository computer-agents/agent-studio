# Real-world online benchmarks

### Email

Initialization: We initialize the mailbox with 100 random emails in the Inbox, 20 in Sent, 10 in Favorites, and 15 in the Recycle Bin. The initialization includes diverse subjects, bodies, and senders to cover the scenarios needed for the following tasks.

These tasks are clear, directly based on the initialized data, and can be automatically checked.
This setup provides a comprehensive benchmark for testing various email operations such as classification, spam filtering, priority sorting, automated replies, and content summarization. The initialization and tasks ensure that agents are tested in a way that mimics real-world use cases. In addition, these tasks are designed to be automatically verifiable. This ensures that each task's success can be programmatically checked, making the evaluation process efficient and reliable.

#### **Task 1: Automatic Classification and Archiving**

1. **Move all emails from `admin@newsletter.com` to a folder named "Newsletters".**
    - **Check**: Verify that all emails from `admin@newsletter.com` are in "Newsletters".
2. **Move all emails with "Project Update" in the subject to a folder named "Work".**
    - **Check**: Verify that all emails with "Project Update" are in the "Work" folder.
3. **Move all emails with "Congratulations" in the subject to a folder named "Promotions".**
    - **Check**: Verify that all emails with "Congratulations" are in the "Promotions" folder.
4. **Archive all emails from `alerts@bank.com`.**
    - **Check**: Verify that all emails from `alerts@bank.com` are in the "Archive" folder.
5. **Move all emails with "Invoice" in the subject to a folder named "Finance".**
    - **Check**: Verify that all emails with "Invoice" are in the "Finance" folder.
6. **Move all emails from `hr@company.com` to a folder named "HR".**
    - **Check**: Verify that all emails from `hr@company.com` are in the "HR" folder.
7. **Move all emails with "Meeting" or "Proposal" in the subject to a folder named "Meetings".**
    - **Check**: Verify that all emails with "Meeting" or "Proposal" in the subject are in the "Meetings" folder.
8. **Move all emails from `client@example.com` and `boss@example.com` to a folder named "Boss".**
    - **Check**: Verify that all emails from `client@example.com` and `boss@example.com` are in the "Boss" folder.
9. **Move all emails in a folder named "Boss" to the "Favorites" folder.**
    - **Check**: Verify that all emails in the "Boss" folder are in the "Favorites" folder.

#### **Task 2: Spam Filtering**

1. **Move all emails from `sales@shop.com` to the "Spam" folder.**
    - **Check**: Verify that all emails from `sales@shop.com` are in the "Spam" folder.
2. **Move all emails with "Special Offer" in the subject to the "Spam" folder.**
    - **Check**: Verify that all emails with "Special Offer" are in the "Spam" folder.
3. **Move all emails with "Prize" in the subject to the "Spam" folder.**
    - **Check**: Verify that all emails with "Prize" in the subject are in the "Spam" folder.
4. **Move all emails from `spam@phishing.com` to the "Spam" folder.**
    - **Check**: Verify that all emails from `spam@phishing.com` are in the "Spam" folder.
5. **Move all emails with "Congratulations" in the subject to the "Spam" folder.**
    - **Check**: Verify that all emails with "Congratulations" are in the "Spam" folder.
6. **Move all emails from `no-reply@service.com` to the "Spam" folder.**
    - **Check**: Verify that all emails from `no-reply@service.com` are in the "Spam" folder.
7. **Move all emails from `newsletter@ads.com` to the "Spam" folder.**
    - **Check**: Verify that all emails from `newsletter@ads.com` are in the "Spam" folder.
8. **Move all emails with "Free Gift" in the subject to the "Spam" folder.**
    - **Check**: Verify that all emails with "Free Gift" in the subject are in the "Spam" folder.
9. **Move all emails from unknown senders to the "Spam" folder.**
    - **Check**: Verify that all emails from unknown senders are in the "Spam" folder.
10. **Move all emails with "Click Here" in the body to the "Spam" folder.**
    - **Check**: Verify that all emails with "Click Here" in the body are in the "Spam" folder.

#### **Task 3: Priority Sorting**

1. **Sort emails by sender so that emails from `boss@example.com` are at the top of the inbox.**
    - **Check**: Verify that emails from `boss@example.com` are listed first.
2. **Sort all emails with "Urgent" in the subject to be at the top of the Inbox.**
    - **Check**: Verify that these emails are at the top of the Inbox.
3. **Sort emails from `alerts@bank.com` as high priority.**
    - **Check**: Verify that these emails are listed first in the Inbox.
4. **Sort all unread emails above read ones in the Inbox.**

    - **Check**: Verify that unread emails are listed above read emails.

5. **Sort emails with "Security" in the subject to be second in the priority list.**
    - **Check**: Verify that these emails are listed second in the Inbox.
6. **Sort emails with "Project Update" in the subject as medium priority.**
    - **Check**: Verify that these emails are listed in the middle of the Inbox.
7. **Sort emails from `manager@example.com` above all other emails.**
    - **Check**: Verify that emails from `manager@example.com` are listed first.
8. **Sort emails with "Meeting" in the subject to be above other non-priority emails.**
    - **Check**: Verify that these emails are listed before non-priority emails.
9. **Sort personal emails from `friend@example.com` after work-related ones.**
    - **Check**: Verify that personal emails are listed after work-related ones.
10. **Sort emails with attachments at a higher priority than those without.**
    - **Check**: Verify that emails with attachments are listed before those without.

#### **Task 4: Automatic Reply/Send of Emails**

1. **Auto-reply to all emails from `friend@example.com` with a message "I will get back to you soon."**
    - **Check**: Verify that a reply is sent for each email from `friend@example.com`.
2. **Automatically send a follow-up email to `client@example.com` after three days.**
    - **Check**: Verify that the follow-up email is sent after three days.
3. **Auto-reply to all emails received from `alerts@bank.com` with a confirmation message.**
    - **Check**: Verify that the confirmation message was sent in reply to each email from `alerts@bank.com`.
4. **Send a thank-you email to all recipients in the Sent folder who received emails with "Order Confirmation" in the subject.**
    - **Check**: Verify that thank-you emails were sent to these recipients.
5. **Automatically send an out-of-office reply to any emails received from `support@company.com`.**
    - **Check**: Verify that an out-of-office reply was sent to each email from `support@company.com`.
6. **Auto-reply to all emails from `newsletter@shopping.com` with a message "Thank you for your purchase!"**
    - **Check**: Verify that the reply is sent for each email from `newsletter@shopping.com`.
7. **Automatically send a reminder email to `boss@example.com` two days after a "Project Update" email is received.**
    - **Check**: Verify that the reminder email is sent after two days.
8. **Reply to all emails from `team@project.com` with a project status update.**
    - **Check**: Verify that a project status update is sent in reply to each email from `team@project.com`.
9. **Automatically send a follow-up email to `hr@company.com` one week after receiving a "Policy Update" email.**
    - **Check**: Verify that the follow-up email is sent after one week.
10. **Auto-reply to all emails received outside of business hours with an "Out of Office" message.**
    - **Check**: Verify that an out-of-office reply was sent to all emails received outside of business hours.

#### **Task 5: Summarization and Refinement**

1. **Summarize all emails with "Weekly Report" in the subject into a single summary.**
    - **Check**: Verify that the summary contains the key points from all such emails.
2. **Refine the draft of an email intended for `client@example.com` to be more formal.**
    - **Check**: Verify that the refined email has a more formal tone and structure.
3. **Summarize all emails in the "Work" folder into a concise project update.**
    - **Check**: Verify that the update reflects the content of the emails in the "Work" folder.
4. **Refine the automatic reply to `friend@example.com` to include a personal touch.**
    - **Check**: Verify that the reply is more personalized.
5. **Summarize all emails from `hr@company.com` regarding policy updates into a single document.**
    - **Check**: Verify that the document includes all key updates from the HR emails.
6. **Summarize all emails from `alerts@bank.com` about security issues into one report.**
    - **Check**: Verify that the report includes all security-related information from the emails.
7. **Refine the draft of a follow-up email to `manager@example.com` to ensure clarity.**
    - **Check**: Verify that the refined email is clear and concise.
8. **Summarize all client emails in the "Clients" folder into one comprehensive report.**
    - **Check**: Verify that the report includes all relevant client communication.
9. **Refine the response email to `support@company.com` for a support ticket to be more detailed.**
    - **Check**: Verify that the response email includes all necessary details.
10. **Summarize all emails with "Proposal" in the subject into a summary document for review.**
    - **Check**: Verify that the summary document accurately reflects the contents of these emails.

## Example tasks

The example task configurations are located in `evals/online_benchmarks/tasks`.

We also provide more auto-evaluators on other applications in `agent_studio/envs/desktop_env/evaluators`, such as Google Drive, Google Slides, etc.

## Evaluate agents on custom tasks

### Before You Start

You should note that the toolkit may do some **non-reversible actions**, such as deleting files, creating files, running commands, and deleting Google Calendar events. Please make sure you are hosting the toolkit in **a safe environment (E.g. virtual machine or docker) or have backups of your data.** Some tasks may require you to provide API keys. Before running the tasks, **please make sure the account doesn't have important data.**

### Run benchmark

#### Non-GUI tasks

For Level-1 tasks without Google API usage (e.g., OS-related tasks), you can directly run:

For example:

```bash
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/filesystem --model gemini-1.0-pro-001
```

You can set `need_human_confirmation` to True in `agent_studio/config/config.py` to do safety check before each action execution. You can add `--help` for more args.

By default, you can check `logs` to see the full logs and result jsonl files.

Google service related tasks requiring Google API usage, kindly enable Google APIs, configure OAuth, download the credentials following instructions [here](https://developers.google.com/docs/api/quickstart/python#set_up_your_environment), specify the credential path in `agent_studio/config/api_key.json`. When you run the benchmark for the first time, you will be prompted to visit several URLs to authorize Google Docs, Drives, etc. The corresponding token json files like `docs_token.json` will be saved in `agent_studio/config`.

Start benchmarking:

```bash
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/vscode/ --model gemini-1.0-pro-001
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/docs --model gemini-1.0-pro-001
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/filesystem --model gemini-1.0-pro-001
```

#### GUI tasks

This setup is suitable for evaluating agents in visual tasks. For reproducibility, we use a Ubuntu docker container connected via VNC remote desktop.

```bash
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/vscode/ --model gemini-1.5-flash-001 --remote --render
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/vscode/ --model gemini-1.5-flash-001 --remote ...
```

#### Human Evaluation

In case you want to debug or evaluate human performance, this testsuite also supports human evaluation. To enter human evaluation mode, you should set `--agent` to `human` and set `--need_human_confirmation` to True. During the evaluation, the script will popup "Confirm when you finish" after resetting the task. You can now do the task manually in any vnc viewer. After finishing the task, you can confirm the popup message to see the evaluation result. **You should only confirm the popup message after you have finished the task.**

Example command to start human evaluation on vscode tasks:

```bash
as-online-benchmark --task_configs_path evals/online_benchmarks/tasks/basic/vscode/ --model gemini-1.5-flash-001 --agent human --remote --render --need_human_confirmation
```

## Add more tasks

To add custom tasks for benchmarking agents in the wild, you can add a task.jsonl files according to ...

This guide provides instructions for creating a valid Task JSON file in accordance with the specified schema for task evaluation. The JSON file combines details about the environment and tasks, along with various parameters pertinent to the evaluation process.

### Task Structure

-   `task_id`: A unique identifier for the task.
-   `instruction`: The task instuction.
-   `tags`: (optional) A list of tags to categorize the task.
-   `visual`:
-   `max_steps`:
-   `evals`: A list of evaluators to evaluate the task. Each object in the list should include:
    -   `eval_type`: The type of evaluation to be conducted. This should match the name of the evaluator.
    -   `eval_procedure`: (optional) Contains the evaluation procedure and the reference answers.
    -   `reset_procedure`: (optional) A list of actions to reset environment before the task.

Example task:

```json
{
    "task_id": "uuid string",
    "instruction": "Task instruction for the agent to complete",
    "tags": ["tag1", "tag2"],
    "visual": false,
    "max_steps": 1,
    "eval_procedure": [
        {
            "evaluator": "evaluator1",
            "function": "function1",
            "params": {
                "param1": "value1"
            }
        }
    ],
    "reset_procedure": [
        {
            "evaluator": "evaluator2",
            "function": "function1",
            "params": {
                "param1": "value1",
                "param2": "value2"
            }
        }
    ]
}
```
