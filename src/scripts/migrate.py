from migrations.run import pending_migrations, run_migrations


def main():
    pending = pending_migrations()
    if not pending:
        print('No pending migrations')
        return

    print(f'Running migrations: {", ".join(pending)}')
    run_migrations()
    print('Done')


if __name__ == '__main__':
    main()
