"""Streamlit UI for Folder Tokenizer."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from folder_tokenizer.tokenizer import DEFAULT_MODEL, POPULAR_MODELS, FolderTokenizer


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Folder Tokenizer",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Folder Tokenizer")
    st.markdown(
        "Analyze token counts for all documents in a folder using HuggingFace tokenizers."
    )

    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Model selection
        st.subheader("Tokenizer Model")

        model_options = {name: label for name, label in POPULAR_MODELS}
        model_choice = st.selectbox(
            "Select a model",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            index=0,
        )

        # Custom model input
        use_custom = st.checkbox("Use custom model")
        if use_custom:
            custom_model = st.text_input(
                "HuggingFace model name",
                placeholder="e.g., facebook/opt-1.3b",
            )
            model_name = custom_model if custom_model else model_choice
        else:
            model_name = model_choice

        st.divider()

        # Help section
        st.subheader("📖 Supported Files")
        st.markdown("""
        - **Text**: .txt, .md, .json, .csv, .xml, .yaml
        - **Code**: .py, .js, .ts, .java, .go, .rs, etc.
        - **Documents**: .pdf, .docx
        - **Images**: .png, .jpg (OCR)
        - **Archives**: .zip (auto-extracted)
        """)

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        folder_path = st.text_input(
            "📁 Folder Path",
            placeholder="/path/to/your/folder",
            help="Enter the full path to the folder you want to analyze",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)

    # Analysis section
    if analyze_button:
        if not folder_path:
            st.error("Please enter a folder path.")
            return

        path = Path(folder_path)
        if not path.exists():
            st.error(f"Folder not found: {folder_path}")
            return

        if not path.is_dir():
            st.error(f"Not a directory: {folder_path}")
            return

        # Run analysis
        with st.spinner("Loading tokenizer..."):
            try:
                tokenizer = FolderTokenizer(model_name=model_name)
                # Pre-load the tokenizer
                _ = tokenizer.tokenizer
            except Exception as e:
                st.error(f"Failed to load tokenizer: {e}")
                return

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(current: int, total: int, file_result):
            progress = current / total if total > 0 else 0
            progress_bar.progress(progress)
            status_text.text(f"Processing {current}/{total}: {Path(file_result.path).name}")

        # Process folder
        with st.spinner("Analyzing folder..."):
            try:
                result = tokenizer.process_folder(folder_path, progress_callback=progress_callback)
            except Exception as e:
                st.error(f"Error processing folder: {e}")
                return

        progress_bar.empty()
        status_text.empty()

        # Display results
        st.success("✅ Analysis complete!")

        # Summary metrics
        st.subheader("📈 Summary")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Tokens", format_number(result.total_tokens))
        with col2:
            st.metric("Total Characters", format_number(result.total_chars))
        with col3:
            st.metric("Files Processed", format_number(result.successful_files))
        with col4:
            st.metric("Failed Files", format_number(result.failed_files))

        # Breakdown by file type
        if result.by_type:
            st.subheader("📊 Breakdown by File Type")

            type_data = []
            for file_type, stats in result.by_type.items():
                type_data.append({
                    "File Type": file_type.capitalize(),
                    "Files": stats["files"],
                    "Tokens": stats["tokens"],
                    "Characters": stats["chars"],
                    "Avg Tokens/File": stats["tokens"] // stats["files"] if stats["files"] > 0 else 0,
                })

            df_types = pd.DataFrame(type_data)
            df_types = df_types.sort_values("Tokens", ascending=False)
            st.dataframe(df_types, use_container_width=True, hide_index=True)

            # Bar chart
            chart_data = df_types.set_index("File Type")["Tokens"]
            st.bar_chart(chart_data)

        # Detailed file results
        st.subheader("📋 Detailed Results")

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["All Files", "Failed Files", "Top Files by Tokens"])

        with tab1:
            file_data = []
            for fr in result.file_results:
                file_data.append({
                    "File": Path(fr.path).name,
                    "Path": fr.path,
                    "Type": fr.file_type,
                    "Tokens": fr.tokens,
                    "Characters": fr.chars,
                    "Status": "✅" if fr.success else "❌",
                    "Error": fr.error or "",
                    "Archive": fr.source_archive or "",
                })

            df_files = pd.DataFrame(file_data)
            st.dataframe(
                df_files,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tokens": st.column_config.NumberColumn(format="%d"),
                    "Characters": st.column_config.NumberColumn(format="%d"),
                },
            )

        with tab2:
            failed_files = [fr for fr in result.file_results if not fr.success]
            if failed_files:
                failed_data = [{
                    "File": Path(fr.path).name,
                    "Path": fr.path,
                    "Type": fr.file_type,
                    "Error": fr.error or "Unknown error",
                } for fr in failed_files]
                st.dataframe(pd.DataFrame(failed_data), use_container_width=True, hide_index=True)
            else:
                st.info("No failed files! 🎉")

        with tab3:
            successful_files = [fr for fr in result.file_results if fr.success]
            top_files = sorted(successful_files, key=lambda x: x.tokens, reverse=True)[:20]
            if top_files:
                top_data = [{
                    "File": Path(fr.path).name,
                    "Type": fr.file_type,
                    "Tokens": fr.tokens,
                    "Characters": fr.chars,
                } for fr in top_files]
                st.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)
            else:
                st.info("No files processed successfully.")

        # Export options
        st.subheader("💾 Export Results")
        col1, col2 = st.columns(2)

        with col1:
            # CSV export
            csv_data = df_files.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="token_analysis.csv",
                mime="text/csv",
            )

        with col2:
            # JSON export
            json_data = {
                "summary": {
                    "folder_path": result.folder_path,
                    "model_name": result.model_name,
                    "total_tokens": result.total_tokens,
                    "total_chars": result.total_chars,
                    "total_files": result.total_files,
                    "successful_files": result.successful_files,
                    "failed_files": result.failed_files,
                },
                "by_type": result.by_type,
                "files": [{
                    "path": fr.path,
                    "tokens": fr.tokens,
                    "chars": fr.chars,
                    "file_type": fr.file_type,
                    "success": fr.success,
                    "error": fr.error,
                    "source_archive": fr.source_archive,
                } for fr in result.file_results],
            }
            st.download_button(
                label="📥 Download JSON",
                data=json.dumps(json_data, indent=2),
                file_name="token_analysis.json",
                mime="application/json",
            )

    # Footer
    st.divider()
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Folder Tokenizer • Using HuggingFace Transformers"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
