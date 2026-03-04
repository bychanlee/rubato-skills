---
name: psi-add-computer
user-invokable: true
description: Register a new computer in the project registry
argument-hint: "<name> <type> [hostname:...] [user:...] [scheduler:...] [work_dir:...]"
---

Register a new computer for use in psi calculations.

## Usage

```
psi:add-computer <name> <type> [hostname:...] [user:...] [scheduler:...] [work_dir:...] [queues:...] [modules:...] [env_setup:...]
```

**You** parse the keyword arguments into a JSON object. Then run:

## Execution

```bash
python {skill_dir}/add_computer.py <name> '<json>'
```

If type is `hpc`, check SSH connectivity afterward and provide setup instructions if disconnected.

## HPC Discovery

When registering an HPC computer, gather job submission details **before** finalizing the config. Use a combination of web search and live SSH commands:

1. **Search official docs**: Use web search for the system's user guide (e.g., `"<system_name> user guide"`, `"<system_name> job submission"`). Look for:
   - Available queues/partitions and their limits (node count, walltime, purpose)
   - Account/allocation/project charging policy
   - Sample job scripts
   - Scheduler type (Slurm, PBS, etc.) and key directives

2. **Discover from the live system** (via SSH):
   - **Work directory**: `echo $SCRATCH`, `echo $WORK`, `df -h`
   - **Queues**: `sinfo -s` (Slurm) or `qstat -Q` (PBS)
   - **Account**: `sacctmgr show assoc user=$USER` (Slurm) or check allocation docs
   - **Modules**: `module avail` for available software
   - **Software paths**: `which pw.x`, `which vasp_std`, etc.

3. **Store discovered details** in the computer config:
   - `scheduler`: scheduler type (e.g., `slurm`, `pbs`)
   - `queues`: list of relevant queues with brief notes
   - `account`: allocation/project name (ask user if not discoverable)
   - `job_template`: a minimal working job script template for this system

4. **Ask the user** for anything ambiguous — never guess accounts, allocations, or queue selection.

## Rules

- **The computer registry is project-local at `calc_db/computers.yaml`.** Run `/psi-init` before adding computers.
- **NEVER hardcode or guess remote environment details.** All remote information must be discovered from official docs, the live system, or confirmed by the user.

## SSH ControlMaster Setup

If SSH is disconnected, print these instructions:

```
# Add to ~/.ssh/config:
Host <alias>
    HostName <hostname>
    User <user>
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist yes
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Start persistent connection:
ssh -MNf <alias>

# Check connection:
ssh -O check <alias>
```
