#!/usr/bin/env python3
"""
Identify missing species for REST API download.

This script compares local zarr species with REST API availability,
keeping in mind that any new species must match zarr dimensions (11619 x 26164).
"""

import zarr
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from bigmap.api import BigMapRestClient

console = Console()

def main():
    try:
        # Load local zarr
        console.print("[bold blue]Loading local zarr file...[/bold blue]")
        arr = zarr.open('./output/nc_biomass_expandable.zarr', mode='r')
        
        # Extract species codes from local zarr
        local_species = set()
        for code in arr.attrs.get('species_codes', []):
            if code.startswith('SPCD'):
                local_species.add(code[4:8])  # Extract just the 4-digit code
        
        console.print(f"[green]✓[/green] Zarr dimensions: {arr.shape}")
        console.print(f"[green]✓[/green] Local species count: {len(local_species)}")
        
        # Get REST API species
        console.print("\n[bold blue]Fetching REST API species...[/bold blue]")
        client = BigMapRestClient()
        api_species_list = client.list_available_species()
        api_species = {s['species_code'] for s in api_species_list}
        
        console.print(f"[green]✓[/green] REST API species count: {len(api_species)}")
        
        # Find missing species
        missing_species = api_species - local_species
        
        # Create summary table
        table = Table(title="Species Coverage Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="yellow")
        table.add_column("Details", style="green")
        
        table.add_row("Zarr Dimensions", f"{arr.shape[1]} x {arr.shape[2]}", "Fixed spatial grid")
        table.add_row("Current Layers", str(arr.shape[0]), f"{len(local_species)} species")
        table.add_row("REST API Available", str(len(api_species)), "Total downloadable")
        table.add_row("Missing Species", str(len(missing_species)), "Can be downloaded")
        
        console.print("\n")
        console.print(table)
        
        # Show some missing species examples
        if missing_species:
            console.print(f"\n[bold yellow]First 20 missing species:[/bold yellow]")
            missing_sorted = sorted(missing_species)
            
            # Create species table with names
            species_table = Table()
            species_table.add_column("Species Code", style="cyan")
            species_table.add_column("Species Name", style="green")
            
            species_dict = {s['species_code']: s['common_name'] for s in api_species_list}
            
            for code in missing_sorted[:20]:
                species_table.add_row(code, species_dict.get(code, "Unknown"))
            
            console.print(species_table)
            
            # Dimensional constraint warning
            warning = Panel(
                "[bold red]IMPORTANT:[/bold red] All downloaded species must be clipped and resampled to "
                f"match zarr dimensions ([yellow]{arr.shape[1]} x {arr.shape[2]}[/yellow]) before adding to zarr.\n\n"
                "[bold blue]Next steps:[/bold blue]\n"
                "1. Use 'bigmap download-species-api --species-code XXXX' to download\n"
                "2. Clip/resample to match NC boundary and zarr grid\n"
                "3. Add to zarr using existing append functionality",
                title="Dimensional Constraints",
                border_style="red"
            )
            console.print("\n")
            console.print(warning)
        
        console.print(f"\n[bold green]Analysis complete![/bold green] {len(missing_species)} species available for download.")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 