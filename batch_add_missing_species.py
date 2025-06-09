#!/usr/bin/env python3
"""
Batch process all missing species from REST API and add them to zarr.

This script:
1. Identifies all species available via REST API but missing from zarr
2. Processes them in batches with proper error handling
3. Provides detailed progress tracking and statistics
4. Handles network failures and retries gracefully
"""

import numpy as np
import zarr
import time
import json
from pathlib import Path
from typing import List, Dict, Set
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, 
    BarColumn, 
    TextColumn, 
    TimeRemainingColumn,
    SpinnerColumn,
    MofNCompleteColumn
)
from rich.layout import Layout
from rich.live import Live

from bigmap.api import BigMapRestClient
from add_api_species_to_zarr import APISpeciesProcessor
from bigmap.console import print_info, print_success, print_error, print_warning

console = Console()

class BatchSpeciesProcessor:
    """Handles batch processing of multiple species from REST API to zarr."""
    
    def __init__(self, zarr_path: str = "./output/nc_biomass_expandable.zarr"):
        self.zarr_path = zarr_path
        self.client = BigMapRestClient()
        self.processor = APISpeciesProcessor(zarr_path)
        
        # Processing statistics
        self.stats = {
            'total_species': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'errors': []
        }
        
        # Configuration
        self.batch_size = 5  # Conservative batch size
        self.retry_failed = True
        self.max_retries = 3
        self.delay_between_species = 2.0  # Respect rate limits
        
    def identify_missing_species(self) -> List[Dict]:
        """Identify all species missing from zarr that are available via API."""
        console.print("\n[bold blue]🔍 Identifying Missing Species[/bold blue]")
        
        # Get current zarr species
        zarr_array = zarr.open_array(self.zarr_path, mode='r')
        local_species = set()
        for code in zarr_array.attrs.get('species_codes', []):
            if code.startswith('SPCD'):
                local_species.add(code[4:8])  # Extract 4-digit code
        
        # Get REST API species
        api_species_list = self.client.list_available_species()
        api_species = {s['species_code'] for s in api_species_list}
        
        # Find missing species
        missing_codes = api_species - local_species
        
        # Create detailed list with names
        missing_species = []
        species_dict = {s['species_code']: s for s in api_species_list}
        
        for code in sorted(missing_codes):
            if code in species_dict:
                missing_species.append({
                    'species_code': code,
                    'common_name': species_dict[code]['common_name'],
                    'scientific_name': species_dict[code]['scientific_name']
                })
        
        # Update statistics
        self.stats['total_species'] = len(missing_species)
        
        # Show summary
        summary_table = Table(title="Missing Species Analysis")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="yellow")
        
        summary_table.add_row("Current zarr species", str(len(local_species)))
        summary_table.add_row("REST API species", str(len(api_species)))
        summary_table.add_row("Missing species", str(len(missing_species)))
        summary_table.add_row("Zarr shape", str(zarr_array.shape))
        
        console.print(summary_table)
        
        if missing_species:
            console.print(f"\n[green]Found {len(missing_species)} species to process[/green]")
            console.print("First 10 missing species:")
            
            preview_table = Table()
            preview_table.add_column("Code", style="cyan")
            preview_table.add_column("Common Name", style="green")
            
            for species in missing_species[:10]:
                preview_table.add_row(
                    species['species_code'],
                    species['common_name']
                )
            
            console.print(preview_table)
            
            if len(missing_species) > 10:
                console.print(f"... and {len(missing_species) - 10} more species")
        
        return missing_species
    
    def process_species_batch(self, species_batch: List[Dict], batch_num: int, total_batches: int) -> Dict:
        """Process a batch of species."""
        batch_stats = {'successful': 0, 'failed': 0, 'errors': []}
        
        console.print(f"\n[bold yellow]📦 Processing Batch {batch_num}/{total_batches}[/bold yellow]")
        console.print(f"Species in this batch: {len(species_batch)}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            batch_task = progress.add_task(
                f"Batch {batch_num}", 
                total=len(species_batch)
            )
            
            for i, species in enumerate(species_batch):
                species_code = species['species_code']
                species_name = species['common_name']
                
                progress.update(
                    batch_task, 
                    description=f"Processing {species_code} ({species_name})"
                )
                
                try:
                    # Add delay between species to respect rate limits
                    if i > 0:
                        time.sleep(self.delay_between_species)
                    
                    # Process the species
                    self.processor.process_species(species_code, species_name)
                    
                    batch_stats['successful'] += 1
                    self.stats['successful'] += 1
                    
                    print_success(f"✅ {species_code} ({species_name}) - Added successfully")
                    
                except Exception as e:
                    error_msg = f"Failed to process {species_code} ({species_name}): {str(e)}"
                    batch_stats['failed'] += 1
                    self.stats['failed'] += 1
                    batch_stats['errors'].append(error_msg)
                    self.stats['errors'].append(error_msg)
                    
                    print_error(f"❌ {species_code} ({species_name}) - {str(e)}")
                
                self.stats['processed'] += 1
                progress.update(batch_task, advance=1)
        
        return batch_stats
    
    def save_progress_log(self, filename: str = "batch_processing_log.json"):
        """Save processing statistics and errors to a log file."""
        log_data = {
            'processing_stats': self.stats.copy(),
            'zarr_path': self.zarr_path,
            'batch_size': self.batch_size,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add duration if processing started
        if self.stats['start_time']:
            log_data['duration_seconds'] = time.time() - self.stats['start_time']
        
        with open(filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print_info(f"Progress log saved to {filename}")
    
    def show_final_summary(self):
        """Display final processing summary."""
        duration = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        
        # Final zarr state
        zarr_array = zarr.open_array(self.zarr_path, mode='r')
        final_shape = zarr_array.shape
        final_species_count = zarr_array.attrs['n_species']
        
        # Create summary table
        summary_table = Table(title="Batch Processing Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow")
        
        summary_table.add_row("Total Species to Process", str(self.stats['total_species']))
        summary_table.add_row("Successfully Added", str(self.stats['successful']))
        summary_table.add_row("Failed", str(self.stats['failed']))
        summary_table.add_row("Processing Time", f"{duration/60:.1f} minutes")
        summary_table.add_row("Final Zarr Shape", str(final_shape))
        summary_table.add_row("Final Species Count", str(final_species_count))
        
        if self.stats['successful'] > 0:
            avg_time = duration / self.stats['successful']
            summary_table.add_row("Avg Time per Species", f"{avg_time:.1f} seconds")
        
        console.print("\n")
        console.print(summary_table)
        
        # Show errors if any
        if self.stats['failed'] > 0:
            console.print(f"\n[bold red]❌ Errors encountered:[/bold red]")
            for error in self.stats['errors'][-5:]:  # Show last 5 errors
                console.print(f"  • {error}")
            
            if len(self.stats['errors']) > 5:
                console.print(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        # Final status panel
        if self.stats['failed'] == 0:
            status_color = "green"
            status_msg = "🎉 All species processed successfully!"
        elif self.stats['successful'] > 0:
            status_color = "yellow"
            status_msg = f"⚠️ Partial success: {self.stats['successful']} added, {self.stats['failed']} failed"
        else:
            status_color = "red"
            status_msg = "❌ Processing failed for all species"
        
        final_panel = Panel(
            status_msg,
            title="Final Status",
            border_style=status_color
        )
        console.print("\n")
        console.print(final_panel)
    
    def run_batch_processing(self):
        """Main batch processing workflow."""
        console.print("[bold blue]🚀 BigMap Batch Species Processing[/bold blue]")
        console.print(f"Target zarr: {self.zarr_path}")
        console.print(f"Batch size: {self.batch_size}")
        console.print()
        
        try:
            # Step 1: Identify missing species
            missing_species = self.identify_missing_species()
            
            if not missing_species:
                console.print("[bold green]✅ No missing species found! Zarr is up to date.[/bold green]")
                return
            
            # Confirm processing
            console.print(f"\n[bold yellow]⚠️ About to process {len(missing_species)} species[/bold yellow]")
            console.print("This will:")
            console.print("• Download rasters from REST API")
            console.print("• Align them to zarr spatial grid")
            console.print("• Add them as new zarr layers")
            console.print(f"• Take approximately {len(missing_species) * 10 / 60:.1f} minutes")
            
            response = input("\nProceed? [y/N]: ").lower()
            if not response.startswith('y'):
                console.print("Processing cancelled.")
                return
            
            # Step 2: Process in batches
            self.stats['start_time'] = time.time()
            total_batches = (len(missing_species) + self.batch_size - 1) // self.batch_size
            
            console.print(f"\n[bold green]🏁 Starting batch processing...[/bold green]")
            console.print(f"Processing {len(missing_species)} species in {total_batches} batches")
            
            for batch_num in range(total_batches):
                start_idx = batch_num * self.batch_size
                end_idx = min(start_idx + self.batch_size, len(missing_species))
                species_batch = missing_species[start_idx:end_idx]
                
                try:
                    batch_stats = self.process_species_batch(
                        species_batch, 
                        batch_num + 1, 
                        total_batches
                    )
                    
                    print_info(f"Batch {batch_num + 1} complete: "
                             f"{batch_stats['successful']} successful, "
                             f"{batch_stats['failed']} failed")
                    
                    # Save progress after each batch
                    self.save_progress_log()
                    
                except KeyboardInterrupt:
                    console.print("\n[bold red]⚠️ Processing interrupted by user[/bold red]")
                    break
                except Exception as e:
                    console.print(f"\n[bold red]❌ Batch {batch_num + 1} failed: {e}[/bold red]")
                    continue
            
            # Step 3: Show final summary
            self.show_final_summary()
            self.save_progress_log("batch_processing_final.json")
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Batch processing failed: {e}[/bold red]")
            raise

def main():
    """Main entry point."""
    processor = BatchSpeciesProcessor()
    processor.run_batch_processing()

if __name__ == "__main__":
    main() 