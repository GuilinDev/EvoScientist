"""Slash commands for skill management: /skills, /install-skill, /uninstall-skill."""

from ..stream.display import console
from .agent import _shorten_path


def _cmd_list_skills() -> None:
    """List installed user skills."""
    from ..tools.skills_manager import list_skills
    from ..paths import USER_SKILLS_DIR

    skills = list_skills(include_system=False)

    if not skills:
        console.print("[dim]No user-installed skills.[/dim]")
        console.print("[dim]Install with:[/dim] /install-skill <path-or-url>")
        console.print(f"[dim]Skills directory:[/dim] [cyan]{_shorten_path(str(USER_SKILLS_DIR))}[/cyan]")
        console.print()
        return

    console.print(f"[bold]User-Installed Skills[/bold] ({len(skills)}):")
    for skill in skills:
        console.print(f"  [green]{skill.name}[/green] - {skill.description}")
    console.print(f"\n[dim]Location:[/dim] [cyan]{_shorten_path(str(USER_SKILLS_DIR))}[/cyan]")
    console.print()


def _cmd_install_skill(source: str) -> None:
    """Install a skill from local path or GitHub URL."""
    from ..tools.skills_manager import install_skill

    if not source:
        console.print("[red]Usage:[/red] /install-skill <path-or-url>")
        console.print("[dim]Examples:[/dim]")
        console.print("  /install-skill ./my-skill")
        console.print("  /install-skill https://github.com/user/repo/tree/main/skill-name")
        console.print("  /install-skill user/repo@skill-name")
        console.print()
        return

    console.print(f"[dim]Installing skill from:[/dim] {source}")

    result = install_skill(source)

    if result["success"]:
        console.print(f"[green]Installed:[/green] {result['name']}")
        console.print(f"[dim]Description:[/dim] {result.get('description', '(none)')}")
        console.print(f"[dim]Path:[/dim] [cyan]{_shorten_path(result['path'])}[/cyan]")
        console.print()
        console.print("[dim]Reload with /new to apply.[/dim]")
    else:
        console.print(f"[red]Failed:[/red] {result['error']}")
    console.print()


def _cmd_uninstall_skill(name: str) -> None:
    """Uninstall a user-installed skill."""
    from ..tools.skills_manager import uninstall_skill

    if not name:
        console.print("[red]Usage:[/red] /uninstall-skill <skill-name>")
        console.print("[dim]Use /skills to see installed skills.[/dim]")
        console.print()
        return

    result = uninstall_skill(name)

    if result["success"]:
        console.print(f"[green]Uninstalled:[/green] {name}")
        console.print("[dim]Reload with /new to apply.[/dim]")
    else:
        console.print(f"[red]Failed:[/red] {result['error']}")
    console.print()
