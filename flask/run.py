from app import app

if __name__ == "__main__":
    # Agregar use_reloader=False para timer functions
    app.run(host="0.0.0.0",port="3000",use_reloader=False,debug=True)
