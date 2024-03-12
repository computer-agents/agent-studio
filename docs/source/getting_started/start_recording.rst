# Record Dataset

Start recording:

```bash
python run.py --mode record --env desktop
```

The first screen is a task configuration interface, where you can create a new task or load an existing task. The task configuration interface is shown below:

![](./imgs/recorder_task_config.png)

You can choose to record an existing task or create a new task. The following are the steps to record a task:

+ Record an existing task:
    1. Choose task from the top right list.
    3. Click the "Save Task Config/Start Recording" button to start recording.
    ![](./imgs/recorder_choose_existing.png)
+ Create & Record new task:
    1. Input the task instruction.
    2. Select the task type (whether is a visual task or not).
    3. Select the evaluator from the dropdown list.
    4. Select the evaluator methods from the list table. A single click will display the method description in "Docs" and a double click will show the method example JSON snippet in "JSON format preview".
    5. Edit the "Evaluation Steps" input box, which should be a list of steps to evaluate the task. The format should match the "evals" field in the task configuration JSON format.
    6. Click the "Save Task Config/Start Recording" button to start recording.
    ![](./imgs/recorder_create_new.png)

The recording interface is shown below:

![](./imgs/recorder_record.png)

The recording interface is divided into three parts: the left part is the VNC window, task configuration created in the previous step is displayed in the middle part, and the right part is the "Action" panel. To record a task, you need to perform the following steps:
1. Input actions (currently is Python code) in the "Action" panel.
2. Click the "Step Action" button to execute the actions.
3. See the result in the VNC window and "Runtime Response" panel.
4. Repeat the above steps until the task is completed.
5. Click the "Save" button to save the recording.
