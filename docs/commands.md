# `apple-compose`

Docker Compose-like workflow for Apple Containers.

**Usage**:

```console
$ apple-compose [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `-f, --file FILE`: Compose file path for commands that load Compose config.  [default: docker-compose.yml]
* `--env-file FILE`: Environment file for commands that load Compose config.
* `-p, --project-name TEXT`: Override the Compose project name for Compose-scoped commands.
* `--verbose`: Print container commands.
* `--dry-run`: Print generated container commands without executing.
* `--help`: Show this message and exit.

**Commands**:

* `build`: Build service images.
* `config`: Show a summary of the current Compose file.
* `ls`: List apple-compose projects.
* `up`: Create and start services.
* `down`: Remove service containers.
* `ps`: Show planned services from the current...
* `pull`: Pull service images.
* `images`: Show images referenced by the current...
* `exec`: Execute a command in a running service...
* `run`: Run a one-off service container.
* `start`: Start existing service containers.
* `stop`: Stop running services.
* `restart`: Restart services.
* `rm`: Remove service containers without removing...
* `kill`: Kill running service containers.
* `logs`: Fetch service logs.
* `port`: Show configured published ports for a...
* `stats`: Display service resource usage statistics.
* `volumes`: Show volumes declared by the current...
* `version`: Show the apple-compose version.

## `apple-compose build`

Build service images.

**Usage**:

```console
$ apple-compose build [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to build.

**Options**:

* `--no-cache`: Build without cache.
* `--help`: Show this message and exit.

## `apple-compose config`

Show a summary of the current Compose file.

**Usage**:

```console
$ apple-compose config [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `apple-compose ls`

List apple-compose projects.

**Usage**:

```console
$ apple-compose ls [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `apple-compose up`

Create and start services.

**Usage**:

```console
$ apple-compose up [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to start.

**Options**:

* `-d, --detach`: Run containers detached.
* `--build`: Build images before starting.
* `--no-cache`: Build without cache.
* `--help`: Show this message and exit.

## `apple-compose down`

Remove service containers.

**Usage**:

```console
$ apple-compose down [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to remove.

**Options**:

* `--help`: Show this message and exit.

## `apple-compose ps`

Show planned services from the current Compose file.

**Usage**:

```console
$ apple-compose ps [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `apple-compose pull`

Pull service images.

**Usage**:

```console
$ apple-compose pull [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to pull images for.

**Options**:

* `--help`: Show this message and exit.

## `apple-compose images`

Show images referenced by the current Compose file.

**Usage**:

```console
$ apple-compose images [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to show images for.

**Options**:

* `--help`: Show this message and exit.

## `apple-compose exec`

Execute a command in a running service container. Use -- before command args.

**Usage**:

```console
$ apple-compose exec [OPTIONS] SERVICE [COMMAND]...
```

**Arguments**:

* `SERVICE`: Service to execute the command in.  [required]
* `[COMMAND]...`: Command to execute in the service container.

**Options**:

* `-d, --detach`: Run the command detached.
* `-i, --interactive`: Keep stdin open.
* `-t, --tty`: Allocate a TTY.
* `-u, --user TEXT`: User to run as.
* `-w, --workdir, --cwd TEXT`: Working directory in the container.
* `--help`: Show this message and exit.

## `apple-compose run`

Run a one-off service container. Use -- before command args.

**Usage**:

```console
$ apple-compose run [OPTIONS] SERVICE [COMMAND]...
```

**Arguments**:

* `SERVICE`: Service to run once.  [required]
* `[COMMAND]...`: Command to run instead of the service default.

**Options**:

* `--rm, --remove`: Remove the container after it stops.
* `--help`: Show this message and exit.

## `apple-compose start`

Start existing service containers.

**Usage**:

```console
$ apple-compose start [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to start.

**Options**:

* `--help`: Show this message and exit.

## `apple-compose stop`

Stop running services.

**Usage**:

```console
$ apple-compose stop [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to stop.

**Options**:

* `--signal TEXT`: Signal to send to containers.
* `--time INTEGER`: Seconds to wait before killing containers.
* `--help`: Show this message and exit.

## `apple-compose restart`

Restart services.

**Usage**:

```console
$ apple-compose restart [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to restart.

**Options**:

* `--signal TEXT`: Signal to send when stopping containers.
* `--time INTEGER`: Seconds to wait before killing containers.
* `--help`: Show this message and exit.

## `apple-compose rm`

Remove service containers without removing networks or volumes.

**Usage**:

```console
$ apple-compose rm [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to remove.

**Options**:

* `-f, --force`: Remove containers even if they are running.
* `--help`: Show this message and exit.

## `apple-compose kill`

Kill running service containers.

**Usage**:

```console
$ apple-compose kill [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to kill.

**Options**:

* `-s, --signal TEXT`: Signal to send to containers.
* `--help`: Show this message and exit.

## `apple-compose logs`

Fetch service logs.

**Usage**:

```console
$ apple-compose logs [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to show logs for.

**Options**:

* `--boot`: Show boot log instead of stdio.
* `-f, --follow`: Follow log output.
* `-n INTEGER`: Number of log lines to show.
* `--help`: Show this message and exit.

## `apple-compose port`

Show configured published ports for a service.

**Usage**:

```console
$ apple-compose port [OPTIONS] SERVICE
```

**Arguments**:

* `SERVICE`: Service to show ports for.  [required]

**Options**:

* `--help`: Show this message and exit.

## `apple-compose stats`

Display service resource usage statistics.

**Usage**:

```console
$ apple-compose stats [OPTIONS] [SERVICES]...
```

**Arguments**:

* `[SERVICES]...`: Services to show stats for.

**Options**:

* `--format TEXT`: Output format passed to container stats.
* `--no-stream`: Disable streaming stats.
* `--help`: Show this message and exit.

## `apple-compose volumes`

Show volumes declared by the current Compose file.

**Usage**:

```console
$ apple-compose volumes [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `apple-compose version`

Show the apple-compose version.

**Usage**:

```console
$ apple-compose version [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
