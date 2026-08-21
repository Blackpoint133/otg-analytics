"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text: Frontend technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text JSON.
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text background_indexer technical diagnostic text.

technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text items_index.json, .import_state.json technical diagnostic text current_price.csv
technical diagnostic text write technical diagnostic text technical diagnostic text technical diagnostic text background_indexer.py - technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text:
- background_indexer.py: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text/technical diagnostic text items_index.json
  - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text long-running technical diagnostic text
  - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
  
- data_access.py (technical diagnostic text technical diagnostic text): technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
  - load_items_index(): technical diagnostic text items_index.json (technical diagnostic text technical diagnostic text technical diagnostic text)
  - load_item_data(): technical diagnostic text CSV technical diagnostic text technical diagnostic text (technical diagnostic text)
  - Fail gracefully technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
  
  !! technical diagnostic text: technical diagnostic text technical diagnostic text rebuild, get_or_rebuild technical diagnostic text technical diagnostic text !!

technical diagnostic text technical diagnostic text:
- Full CSV data technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
- technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text)
"""

import os
import sys
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import streamlit as st

from logging_compat import debug, info, error, warning

from config import get_data_dir, get_app_root_dir


# ════════════════════════════════════════════════════════════════════════════════
# SAFETY: technical implementation note technical implementation note - technical implementation note read-only
# ════════════════════════════════════════════════════════════════════════════════

def _assert_no_index_write_functions():
    """
    SAFETY CHECK: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text-technical diagnostic text rebuild technical diagnostic text.
    """
    forbidden_functions = [
        'get_or_rebuild_items_index',
        'rebuild_items_index_from_filesystem',
        'rebuild_items_index',
        '_save_index_file',
        '_write_index',
        'update_index'
    ]
    
    for func_name in forbidden_functions:
        if hasattr(sys.modules[__name__], func_name):
            error_msg = (
                f"technical diagnostic text technical diagnostic text: technical diagnostic text '{func_name}' technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text data_access!\n"
                f"technical diagnostic text technical diagnostic text technical diagnostic text read-only, technical diagnostic text technical diagnostic text technical diagnostic text background_indexer.py.\n"
                f"technical diagnostic text '{func_name}' technical diagnostic text data_access.py technical diagnostic text technical diagnostic text!"
            )
            error(f"[ARCH] {error_msg}")
            raise RuntimeError(error_msg)

# technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
try:
    _assert_no_index_write_functions()
except RuntimeError as e:
    raise


@dataclass
class IndexLoadDiagnostics:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text:
        success: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        items_count: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        error_message: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        errors: technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text technical diagnostic text app.py)
        warnings: technical diagnostic text technical diagnostic text
        rebuild_needed: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    success: bool = False
    items_count: int = 0
    error_message: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rebuild_needed: bool = False
    
    def add_error(self, msg: str):
        """technical documentation technical documentation technical documentation technical documentation."""
        self.errors.append(msg)
        error(msg)
    
    def add_warning(self, msg: str):
        """technical documentation technical documentation."""
        self.warnings.append(msg)
        warning(msg)
    
    def get_summary(self) -> str:
        """technical documentation technical documentation technical documentation."""
        lines = []
        if self.success:
            lines.append(f"✅ technical diagnostic text technical diagnostic text: {self.items_count} technical diagnostic text")
        else:
            lines.append(f"❌ technical diagnostic text technical diagnostic text technical diagnostic text: {self.error_message}")
        
        if self.rebuild_needed:
            lines.append("⚠️ technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text)")
        
        if self.errors:
            lines.append(f"\n❌ technical diagnostic text ({len(self.errors)}):")
            for err in self.errors[:3]:
                lines.append(f"    - {err}")
            if len(self.errors) > 3:
                lines.append(f"    ... technical diagnostic text technical diagnostic text {len(self.errors) - 3}")
        
        if self.warnings:
            lines.append(f"\n⚠️ technical diagnostic text ({len(self.warnings)}):")
            for warn in self.warnings[:3]:
                lines.append(f"    - {warn}")
            if len(self.warnings) > 3:
                lines.append(f"    ... technical diagnostic text technical diagnostic text {len(self.warnings) - 3}")
        
        return "\n".join(lines)


def get_data_directory() -> Path:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Returns:
        Path: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text CSV technical diagnostic text technical diagnostic text
    """
    return get_data_dir() / 'sales'


def get_price_file() -> Path:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text GUN.
    
    Returns:
        Path: technical diagnostic text technical diagnostic text technical diagnostic text current_price.csv
    """
    return get_data_dir() / 'current_price.csv'


def get_items_index_file() -> Path:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Returns:
        Path: technical diagnostic text technical diagnostic text technical diagnostic text items_index.json
    """
    return get_data_dir() / 'items_index.json'


@st.cache_data(ttl=3600)
def load_current_price() -> float:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text GUN technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text 1 technical diagnostic text).
    
    Returns:
        float: technical diagnostic text GUN technical diagnostic text USD, technical diagnostic text technical diagnostic text 0.03
    """
    price_file = get_price_file()
    try:
        if not price_file.exists():
            warning(f"technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text: {price_file}")
            return 0.03
        
        with open(price_file, 'r') as f:
            first_line = f.readline().strip()
            if not first_line:
                warning("technical diagnostic text technical diagnostic text technical diagnostic text")
                return 0.03
            price_str = first_line.split(',')[0]
            return float(price_str)
    except Exception as e:
        warning(f"technical diagnostic text technical diagnostic text technical diagnostic text: {e}, technical diagnostic text technical diagnostic text 0.03")
        return 0.03






def load_items_index() -> Tuple[Dict[str, Any], IndexLoadDiagnostics]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text JSON technical diagnostic text.
    
    technical diagnostic text: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text/technical diagnostic text technical diagnostic text technical diagnostic text:
        from background_indexer import IndexBuilder
        builder = IndexBuilder()
        builder.build_index()
    
    Fail gracefully technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Returns:
        Tuple[Dict, IndexLoadDiagnostics]: (items_index, diagnostics)
    """
    index_file = get_items_index_file()
    diagnostics = IndexLoadDiagnostics()
    items_index = {}
    
    # technical implementation note, technical implementation note technical implementation note technical implementation note technical implementation note
    if not index_file.exists():
        err_msg = (
            f"❌ technical diagnostic text technical diagnostic text technical diagnostic text: {index_file}\n"
            f"technical diagnostic text background_indexer.py technical diagnostic text technical diagnostic text technical diagnostic text:\n"
            f"    python streamlit_opensea_sales/background_indexer.py"
        )
        diagnostics.success = False
        diagnostics.error_message = err_msg
        diagnostics.add_error(err_msg)
        warning(f"[INDEX] {err_msg}")
        return items_index, diagnostics
    
    # technical implementation note technical implementation note JSON
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # technical implementation note technical implementation note technical implementation note technical implementation note technical implementation note
        if isinstance(data, dict) and '_metadata' in data and 'items' in data:
            # technical implementation note technical implementation note: {_metadata: {...}, items: {...}}
            items_index = data['items']
            metadata = data['_metadata']
            debug(f"[INDEX] technical diagnostic text technical diagnostic text technical diagnostic text (v{metadata.get('format_version', '?')})")
        # technical implementation note technical implementation note technical implementation note (technical implementation note items)
        elif isinstance(data, dict) and '_metadata' not in data and 'items' not in data:
            # technical implementation note technical implementation note: {item_key: item, ...}
            items_index = data
            debug("[INDEX] technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text)")
        # technical implementation note list technical implementation note (technical implementation note technical implementation note)
        elif isinstance(data, list):
            items_index = {item['item_key']: item for item in data}
            debug("[INDEX] List technical diagnostic text technical diagnostic text (technical diagnostic text)")
        else:
            raise ValueError(f"technical diagnostic text technical diagnostic text technical diagnostic text: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        
        diagnostics.success = True
        diagnostics.items_count = len(items_index)
        info(f"[INDEX] technical diagnostic text technical diagnostic text: {len(items_index)} technical diagnostic text")
        
    except json.JSONDecodeError as e:
        err_msg = (
            f"❌ technical diagnostic text technical diagnostic text (technical diagnostic text JSON): {e}\n"
            f"technical diagnostic text technical diagnostic text:\n"
            f"    python streamlit_opensea_sales/background_indexer.py"
        )
        diagnostics.success = False
        diagnostics.error_message = err_msg
        diagnostics.add_error(err_msg)
        error(f"[INDEX] {err_msg}")
        
    except Exception as e:
        err_msg = f"❌ technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text: {e}"
        diagnostics.success = False
        diagnostics.error_message = err_msg
        diagnostics.add_error(err_msg)
        error(f"[INDEX] {err_msg}")
    
    return items_index, diagnostics


@st.cache_data(ttl=3600)
def load_item_data(item_file_path: str, file_mtime: float) -> pd.DataFrame:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text CSV technical diagnostic text (technical diagnostic text technical diagnostic text 1 technical diagnostic text).
    
    technical diagnostic text technical diagnostic text technical diagnostic text file_mtime, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    file_mtime technical diagnostic text technical diagnostic text cache buster - technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text 'type':
    - technical diagnostic text technical diagnostic text 'type_token' technical diagnostic text technical diagnostic text 'type' -> technical diagnostic text type_token technical diagnostic text type
    - technical diagnostic text technical diagnostic text technical diagnostic text 'type' technical diagnostic text 'type_token' -> technical diagnostic text type='GUN' technical diagnostic text technical diagnostic text
    
    Args:
        item_file_path: technical diagnostic text technical diagnostic text technical diagnostic text CSV technical diagnostic text
        file_mtime: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text cache invalidation)
    
    Returns:
        pd.DataFrame: technical diagnostic text technical diagnostic text CSV technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text 'type'
    
    Raises:
        FileNotFoundError: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
        pd.errors.ParserError: technical diagnostic text CSV technical diagnostic text
    """
    file_path = Path(item_file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text: {item_file_path}")
    
    try:
        df = pd.read_csv(file_path)
        
        # technical implementation note technical implementation note 'type' technical implementation note technical implementation note technical implementation note charts.py
        # technical implementation note CSV technical implementation note 'type_token' technical implementation note 'type'
        if 'type' not in df.columns:
            if 'type_token' in df.columns:
                # technical implementation note type_token -> technical implementation note technical implementation note technical implementation note type
                df['type'] = df['type_token']
                debug(f"[DATA] technical diagnostic text type technical diagnostic text type_token: {item_file_path}")
            else:
                # technical implementation note type technical implementation note type_token -> default GUN
                df['type'] = 'GUN'
                debug(f"[DATA] technical diagnostic text default type='GUN': {item_file_path}")
        
        debug(f"[DATA] technical diagnostic text technical diagnostic text: {item_file_path} ({len(df)} technical diagnostic text)")
        return df
    
    except Exception as e:
        error_msg = f"technical diagnostic text technical diagnostic text technical diagnostic text CSV: {item_file_path}\n{e}"
        error(f"[DATA] {error_msg}")
        raise


ENRICHMENT_COLUMNS = [
    'gun_usd_price_at_sale',
    'price_usd_at_sale',
    'price_source',
    'price_timestamp',
    'price_resolution',
    'usd_price_confidence',
    'usd_backfilled'
]

PRIMARY_KEY_COLUMNS = ['transaction_hash', 'token_id']
FALLBACK_KEY_COLUMNS = ['sale_date', 'name', 'rarity', 'price_gun', 'seller', 'buyer']
CORE_SALES_COLUMNS = {
    'id',
    'sale_date',
    'name',
    'token_id',
    'price_gun',
    'type_token',
    'rarity',
    'seller',
    'buyer',
    'transaction_hash',
    'item_url',
    'image_url',
    'type',
}


def _clean_key_text(value: Any) -> str:
    if pd.isna(value):
        return ''
    return str(value).strip()


def _normalize_token_id(value: Any) -> str:
    if pd.isna(value):
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.endswith('.0'):
        numeric = pd.to_numeric(pd.Series([text]), errors='coerce').iloc[0]
        if pd.notna(numeric) and float(numeric).is_integer():
            return str(int(numeric))
    return text


def _build_primary_sales_key(df: pd.DataFrame) -> Optional[pd.Series]:
    if not set(PRIMARY_KEY_COLUMNS).issubset(df.columns):
        return None

    transaction_hash = df['transaction_hash'].map(_clean_key_text)
    token_id = df['token_id'].map(_normalize_token_id)
    if (transaction_hash == '').any() or (token_id == '').any():
        return None

    return transaction_hash + '\x1f' + token_id


def _build_fallback_sales_key(df: pd.DataFrame) -> Optional[pd.Series]:
    if not set(FALLBACK_KEY_COLUMNS).issubset(df.columns):
        return None

    sale_date = pd.to_datetime(df['sale_date'], errors='coerce')
    if sale_date.isna().any():
        return None

    price_gun = pd.to_numeric(df['price_gun'], errors='coerce')
    if price_gun.isna().any():
        return None

    key_parts = [
        sale_date.dt.strftime('%Y-%m-%dT%H:%M:%S.%f'),
        df['name'].map(_clean_key_text),
        df['rarity'].map(_clean_key_text),
        price_gun.map(lambda value: f"{float(value):.12g}"),
        df['seller'].map(_clean_key_text),
        df['buyer'].map(_clean_key_text),
    ]

    return key_parts[0].str.cat(key_parts[1:], sep='\x1f')


def _choose_sales_keys(df_original: pd.DataFrame, df_enriched: pd.DataFrame) -> Tuple[Optional[pd.Series], Optional[pd.Series], str]:
    original_key = _build_primary_sales_key(df_original)
    enriched_key = _build_primary_sales_key(df_enriched)
    if original_key is not None and enriched_key is not None:
        return original_key, enriched_key, 'primary'

    original_key = _build_fallback_sales_key(df_original)
    enriched_key = _build_fallback_sales_key(df_enriched)
    if original_key is not None and enriched_key is not None:
        return original_key, enriched_key, 'fallback'

    return None, None, 'none'


def _validate_unique_keys(keys: pd.Series, label: str) -> Optional[str]:
    if keys.isna().any() or (keys == '').any():
        return f'{label}_empty_key'
    if keys.duplicated().any():
        return f'{label}_duplicate_key'
    return None


def _merge_original_with_enriched_columns(
    df_original: pd.DataFrame,
    df_enriched: pd.DataFrame,
    original_key: pd.Series,
    enriched_key: pd.Series,
) -> pd.DataFrame:
    enrichment_columns = [col for col in ENRICHMENT_COLUMNS if col in df_enriched.columns]
    merged = df_original.copy()
    enriched_by_key = df_enriched.loc[:, enrichment_columns].copy()
    enriched_by_key['_sales_key'] = enriched_key.values
    enriched_by_key = enriched_by_key.set_index('_sales_key')

    for col in enrichment_columns:
        if col in CORE_SALES_COLUMNS:
            continue
        merged[col] = original_key.map(enriched_by_key[col])

    if 'gun_usd_price_at_sale' in enrichment_columns:
        merged['gun_usd_price_at_sale'] = pd.to_numeric(merged['gun_usd_price_at_sale'], errors='coerce')
    if 'price_usd_at_sale' in enrichment_columns:
        merged['price_usd_at_sale'] = pd.to_numeric(merged['price_usd_at_sale'], errors='coerce')
    if 'usd_price_confidence' in enrichment_columns:
        merged['usd_price_confidence'] = merged['usd_price_confidence'].fillna('missing')
    if 'usd_backfilled' in enrichment_columns:
        merged['usd_backfilled'] = merged['usd_backfilled'].fillna(False).astype(bool)

    return merged


def _reconcile_original_and_enriched(
    df_original: pd.DataFrame,
    df_enriched: pd.DataFrame,
) -> Tuple[Optional[pd.DataFrame], str]:
    original_key, enriched_key, key_type = _choose_sales_keys(df_original, df_enriched)
    if original_key is None or enriched_key is None:
        return None, 'no_usable_key'

    for keys, label in ((original_key, 'original'), (enriched_key, 'enriched')):
        reason = _validate_unique_keys(keys, label)
        if reason:
            return None, reason

    original_key_set = set(original_key)
    enriched_key_set = set(enriched_key)
    if not enriched_key_set.issubset(original_key_set):
        return None, 'enriched_unknown_keys'

    merged = _merge_original_with_enriched_columns(df_original, df_enriched, original_key, enriched_key)
    if len(merged) != len(df_original):
        return None, 'merged_row_count_mismatch'

    merged_key, _, _ = _choose_sales_keys(merged, df_enriched)
    if merged_key is None or not merged_key.reset_index(drop=True).equals(original_key.reset_index(drop=True)):
        return None, 'original_order_changed'

    if merged_key.duplicated().any():
        return None, 'merged_duplicate_key'

    return merged, f'partial_enriched_merge:{key_type}'


def get_item_record(items_index: Dict[str, Any], item_key: str) -> Optional[Dict[str, Any]]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        items_index: technical diagnostic text technical diagnostic text technical diagnostic text
        item_key: technical diagnostic text technical diagnostic text (technical diagnostic text: "Item Name Rarity")
    
    Returns:
        Optional[Dict]: technical diagnostic text technical diagnostic text technical diagnostic text None technical diagnostic text technical diagnostic text technical diagnostic text
    """
    return items_index.get(item_key)


def get_item_data_from_record(item_record: Dict[str, Any]) -> pd.DataFrame:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text load_item_data() technical diagnostic text file_mtime technical diagnostic text freshness.
    
    technical diagnostic text technical diagnostic text:
    1. technical diagnostic text technical diagnostic text CSV technical diagnostic text items_index.json path (sales/<item>.csv)
    2. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (sales_enriched/<item>.csv)
    3. technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text:
       - technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
       - technical diagnostic text technical diagnostic text technical diagnostic text
       - technical diagnostic text technical diagnostic text transaction_hash technical diagnostic text technical diagnostic text
       - technical diagnostic text technical diagnostic text CSV
    4. technical diagnostic text technical diagnostic text technical diagnostic text: technical diagnostic text technical diagnostic text CSV
    5. Cache base technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text mtime)
    
    Args:
        item_record: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text file_path, file_mtime
    
    Returns:
        pd.DataFrame: DataFrame technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (technical diagnostic text technical diagnostic text technical diagnostic text)
    """
    if not item_record:
        return pd.DataFrame()
    
    file_path = item_record.get('file_path')
    file_mtime = item_record.get('file_mtime', 0.0)
    
    if not file_path:
        return pd.DataFrame()
    
    try:
        # technical implementation note technical implementation note CSV
        df_original = load_item_data(file_path, file_mtime)

        def mark_historical_usd_state(df: pd.DataFrame, available: bool, status: str) -> pd.DataFrame:
            df.attrs['historical_usd_available'] = available
            df.attrs['historical_usd_status'] = status
            return df

        mark_historical_usd_state(df_original, False, 'original_sales_no_enriched')
        
        # technical implementation note technical implementation note technical implementation note technical implementation note
        original_path = Path(file_path)
        enriched_dir = original_path.parent.parent / 'sales_enriched'
        enriched_path = enriched_dir / original_path.name
        
        if enriched_path.exists():
            try:
                # technical implementation note technical implementation note CSV
                df_enriched = pd.read_csv(enriched_path)
                
                # technical implementation note technical implementation note technical implementation note technical implementation note
                required_columns = ENRICHMENT_COLUMNS
                
                missing_columns = [col for col in required_columns if col not in df_enriched.columns]
                if missing_columns:
                    warning(f"[DATA] technical diagnostic text CSV {enriched_path.name} technical diagnostic text technical diagnostic text technical diagnostic text: {missing_columns}")
                    return mark_historical_usd_state(df_original, False, 'enriched_missing_required_columns')
                
                # technical implementation note technical implementation note technical implementation note
                if len(df_enriched) != len(df_original):
                    reconciled_df, reconcile_status = _reconcile_original_and_enriched(df_original, df_enriched)
                    if reconciled_df is None:
                        warning(
                            f"[DATA] {enriched_path.name}: status=enriched_merge_rejected "
                            f"reason={reconcile_status}"
                        )
                        return mark_historical_usd_state(df_original, False, 'enriched_merge_rejected')

                    matched_rows = int(reconciled_df['price_usd_at_sale'].notna().sum())
                    unmatched_rows = len(df_original) - matched_rows
                    info(
                        f"[DATA] {enriched_path.name}: status=partial_enriched_merge "
                        f"original_rows={len(df_original)} enriched_rows={len(df_enriched)} "
                        f"matched_rows={matched_rows} unmatched_original_rows={unmatched_rows}"
                    )
                    return mark_historical_usd_state(reconciled_df, matched_rows > 0, 'partial_enriched_merge')
                
                # technical implementation note technical implementation note transaction_hash technical implementation note technical implementation note
                if 'transaction_hash' in df_original.columns and 'transaction_hash' in df_enriched.columns:
                    original_hashes = set(df_original['transaction_hash'].unique())
                    enriched_hashes = set(df_enriched['transaction_hash'].unique())
                    
                    if original_hashes != enriched_hashes:
                        warning(f"[DATA] technical diagnostic text CSV {enriched_path.name}: transaction_hash set technical diagnostic text technical diagnostic text")
                        return mark_historical_usd_state(df_original, False, 'enriched_hash_mismatch')
                
                # technical implementation note technical implementation note technical implementation note - technical implementation note technical implementation note CSV
                enriched_mtime = enriched_path.stat().st_mtime
                df_enriched = load_item_data(str(enriched_path), enriched_mtime)
                mark_historical_usd_state(
                    df_enriched,
                    'price_usd_at_sale' in df_enriched.columns and df_enriched['price_usd_at_sale'].notna().any(),
                    'enriched_loaded'
                )
                info(f"[DATA] technical diagnostic text technical diagnostic text technical diagnostic text: {enriched_path.name}")
                return df_enriched
                
            except Exception as e:
                warning(f"[DATA] technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text CSV {enriched_path.name}: {e}")
                debug(f"[DATA] Fallback technical diagnostic text technical diagnostic text CSV")
                return mark_historical_usd_state(df_original, False, 'enriched_load_error')
        else:
            # technical implementation note CSV technical implementation note technical implementation note - technical implementation note technical implementation note
            return mark_historical_usd_state(df_original, False, 'enriched_file_missing')
            
    except Exception as e:
        debug(f"[DATA] technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text: {e}")
        return pd.DataFrame()

