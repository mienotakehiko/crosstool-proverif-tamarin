# Instance type of the cloud host

The seven runs at 96 GiB of series L ran on one Amazon EC2 instance of the type `r7i.4xlarge` in the region `ap-northeast-1`. This type has 16 virtual processors and 128 GiB of memory according to the [product page of AWS](https://aws.amazon.com/ec2/instance-types/r7i/). The record [`environment.txt`](environment.txt) of the host states 16 processors and 126,757 MB of memory. The record counts in binary units, so the value equals 123.8 GiB. Every run set a heap limit of 96 GiB.

## Source of the instance type

The instance type comes from an export of the AWS CloudTrail event history with the 13 management events of the instance. The export holds the account identifier, the instance identifier and network addresses. It therefore stays outside this repository, and the last section states its hash.

| Time (UTC, 2026) | Event | Content |
| --- | --- | --- |
| 28 October 03:01:21 | `RunInstances` | Launch with the type `t3.micro` |
| 28 October 05:05:45 | `StopInstances` | Stop |
| 28 October 05:08:56 | `ModifyInstanceAttribute` | Instance type set to `r7i.4xlarge`, accepted by EC2 |
| 28 October 05:10:32 | `StartInstances` | Start |
| 28 October 05:12:24 | `SendSSHPublicKey` | Key for an SSH connection |
| 28 October 05:32:23 | `ModifyInstanceAttribute` | Attribute `instanceInitiatedShutdownBehavior` |
| 28 October 07:06:06 | `StopInstances` | Stop |
| 29 October 01:42:26 | `StartInstances` | Start |
| 29 October 06:51:16 | `StopInstances` | Stop |
| 30 October 01:20:59 | `StartInstances` | Start |
| 30 October 03:19:47 | `StopInstances` | Stop |
| 30 October 03:21:33 | `StartInstances` | Start |
| 30 October 11:54:32 | `StopInstances` | Stop |

All 13 events name one instance, and none reports an error. The export contains one change of the instance type. This change precedes the first start that a run follows, and no further change occurs up to the stop after the last run.

## Runs inside the intervals

The table relates the seven records of [`runs/L/heap96/records.jsonl`](../../runs/L/heap96/records.jsonl) to the intervals between a start and the next stop. The field `time` of a record is the end of its run, and the begin follows from the field `seconds`. Every run begins and ends inside one interval.

| Start (UTC) | Stop (UTC) | Ends of the runs in the interval | Runs |
| --- | --- | --- | ---: |
| 28 October 05:10:32 | 28 October 07:06:06 | 06:42:00 | 1 |
| 29 October 01:42:26 | 29 October 06:51:16 | 04:05:03 and 06:39:40 | 2 |
| 30 October 01:20:59 | 30 October 03:19:47 | 03:03:01 | 1 |
| 30 October 03:21:33 | 30 October 11:54:32 | 05:05:53, 06:37:13 and 09:41:05 | 3 |

The record `environment.txt` carries the time 01:24:20 of 30 October, which lies inside the third interval. An environment record of the first session carries the time 05:34:50 of 28 October. It states 16 processors, and its host name equals the host part of the private DNS name in the launch response. This record contains the host name and stays outside the repository for that reason.

## Hashes of the unpublished evidence

| File | SHA-256 |
| --- | --- |
| CloudTrail export `event_history.json` | `5d43c493880079a332ca6efbe854e603434a99ac8ca7fe764f6a0d54a83cdeaf` |
| Environment record of the first session, `u11_pilot_environment.txt` | `d53481f3d69f160c829f72f250478c514f14394edf97859de566f3563651ac7c` |
