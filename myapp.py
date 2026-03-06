import pandas as pd
import plotly.express as px
import streamlit as st
st.title(":rainbow[SMART DATA INSIGHTS]")
st.set_page_config( 
            page_title="SMART DATA INSIGHTS",
            page_icon="📈",
            layout="wide"
)
st.header("📈 Data-Driven Insights for Smarter Decisions")
st.subheader("Simplifying Data Analysis for Business and Research",divider='rainbow')
file=st.file_uploader('Drop csv or excel file',type=['csv','xlsx'])
if(file!=None):
    if(file.name.endswith('csv')):
        data=pd.read_csv(file)
    else:
        data=pd.read_excel(file)   
    st.download_button(
        label="Download.csv",
         data=data.to_csv(index=True),
        file_name="datawork.csv",
        mime="text/csv"
)
st.dataframe(data)
st.info("file is successfully uploaded",icon='✔️')
c1, c2, c3 = st.columns(3)
c1.metric("Total Records", data.shape[0])
c2.metric("Total Columns", data.shape[1])
c3.metric("Missing Values", data.isnull().sum().sum())
st.subheader(':rainbow[BASIC information of dataset]',divider='rainbow')
tab1,tab2,tab3,tab4=st.tabs(['Summary','Top & Bottom','Data types','Columns'])
with tab1:
    st.write(f"There are {data.shape[0]} rows in dataset & there are {data.shape[1]} columns")
    st.dataframe(data.describe())
with tab2:
    st.subheader(":green[Top Rows]")
    toprows=st.slider("No of Rows you want",1,data.shape[0],key='Top Slider')
    st.dataframe(data.head(toprows))
    st.subheader(":green[Bottom Rows]")
    Bottomrows=st.slider("No of Rows you want",1,data.shape[0],key='Bottom Slider')
    st.dataframe(data.tail(Bottomrows))
with tab3:    
    st.dataframe(data.dtypes)
with tab4:
    st.write("columns:",data.shape[1])
    st.write("column Names:",list(data.columns))
st.subheader(":rainbow[columns values count]",divider="rainbow")
with st.expander("values count"):
    col1,col2=st.columns(2)
    with col1:
       Columns=st.selectbox("choose column name",options= list(data.columns))
    with col2:
        toprows=st.number_input('Top Rows',min_value=1,step=1)
count=st.button("count")
if (count==True):
    result=data[Columns].value_counts().reset_index().head(toprows)
    st.dataframe(result)
st.write('The groupby lets you summarize data by specific groups')
with st.expander("groupby your columns"):
    col1,col2,col3=st.columns(3)
    with col1:
      groupby_cols=st.multiselect('choose your column to groupby',options=list(data.columns))
    with col2:
       operation_cols=st.selectbox('choose column for operation',options=list(data.columns))
    with col3:
        operation=st.selectbox('choose operation',options=['sum','max','min','mean','median'])
    if (groupby_cols):
        result=data.groupby(groupby_cols).agg(newcol=(operation_cols,operation)).reset_index()
    st.dataframe(result) 
st.subheader("Data Visualization",divider='gray')
graphs=st.selectbox('Choose Your Graphs',options=['line','bar','scatter','pie','sunburst',''])
if(graphs=='line'):
    x_axis=st.selectbox('Choose X Axis',options=list(result.columns))
    y_axis=st.selectbox('Choose Y Axis',options=list (result.columns))
    color=st.selectbox('Choose Colors',options=[None]+list(result.columns))
    facet_col=st.selectbox('Choose Additional Columns',options=[None]+list(result.columns))
    fig=px.line(data_frame=result,x=x_axis,y=y_axis,color=color,facet_col=facet_col,marker='o')
    st.plotly_chart(fig)
elif(graphs=='pie'):
    values=st.selectbox('Choose Numerical Values',options=list(result.columns))
    names=st.selectbox('Choose Labels',options=list(result.columns))
    fig=px.pie(data_frame=result,values=values,names=names)
    st.plotly_chart(fig)
elif(graphs=='sunburst'):
    path=st.multiselect('Choose Your Path',options=list(result.columns))
    fig=px.sunburst(data_frame=result,path=path,values='newcol')
    st.plotly_chart(fig)
    
