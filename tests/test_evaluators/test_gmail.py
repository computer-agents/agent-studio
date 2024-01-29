# pytest -s tests/test_evaluators/test_gmail.py
from playground.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_draft_exists": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                                "attachment": "attachment.txt",
                                "cc": "gduser1@workspacesamples.dev",
                            },
                            "exists": True,
                        }
                    }
                ],
                # "reset_procedure": [
                #     {
                #         "create_draft": {
                #             "draft_info": {
                #                 "subject": "Automated draft",
                #                 "recipient": "gduser@workspacesamples.dev",
                #                 "body": "This is automated draft mail",
                #                 "attachment": "attachment.txt",
                #                 "cc": "gduser1@workspacesamples.dev",
                #             }
                #         }
                #     }
                # ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_draft_exists": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                                "attachment": "attachment.txt",
                                "cc": "gduser1@workspacesamples.dev",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_draft": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                                "attachment": "attachment.txt",
                                "cc": "gduser1@workspacesamples.dev",
                            }
                        }
                    }
                ],
            }
        ]
    },
    # {
    #     "evals": [
    #         {
    #             "eval_type": "gmail",
    #             "eval_procedure": [
    #                 {
    #                     "check_sent_email_exists": {
    #                         "sent_email_info": {
    #                             "subject": "Automated Email",
    #                             "body": "This is automatically sent email",
    #                         }
    #                     }
    #                 }
    #             ],
    #             "reset_procedure": [
    #                 {
    #                     "delete_sent_email": {
    #                         "sent_email_info": {
    #                             "subject": "Automated Email",
    #                             "body": "This is automatically sent email",
    #                         }
    #                     }
    #                 }
    #             ],
    #         }
    #     ]
    # },
    # {
    #     "evals": [
    #         {
    #             "eval_type": "gmail",
    #             "eval_procedure": [
    #                 {
    #                     "check_sent_email_exists": {
    #                         "sent_email_info": {
    #                             "subject": "Automated draft",
    #                             "recipient": "gduser1@workspacesamples.dev",
    #                             "body": "This is automated draft mail",
    #                         }
    #                     }
    #                 }
    #             ],
    #             "reset_procedure": [
    #                 {
    #                     "create_draft": {
    #                         "draft_info": {
    #                             "subject": "Automated draft",
    #                             "recipient": "gduser1@workspacesamples.dev",
    #                             "body": "This is automated draft mail",
    #                         }
    #                     },
    #                     "delete_sent_email": {
    #                         "sent_email_info": {
    #                             "subject": "Automated draft",
    #                             "body": "This is automated draft email",
    #                         }
    #                     },
    #                 }
    #             ],
    #         }
    #     ]
    # },
]


def test_gmail():
    for task_config in TASK_CONFIGS:
        comb = evaluator_router(task_config)
        comb.reset()
        score = comb()
        assert score == 1.0
